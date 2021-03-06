#include "TransferringRunner.h"
#include "Parallel.h"
#include "Types.h"
#include <string.h>
#include <list>

using namespace qgate_cuda;
using qgate::QstateIdx;
using qgate::QstateSize;
using qgate::Qone;

namespace  {

template<class V>
struct Context {
    Context(DeviceWorker *worker, V *hostMem, cudaEvent_t evt,
            QstateIdx stride, int nCopyWorkers) :
            worker_(worker), hostMem_(hostMem), evt_(evt),
            ctxEnd_(0), curBegin_(0), curEnd_(0), stride_(stride),
            nCopyWorkers_(nCopyWorkers) { }
    
    DeviceWorker *worker_;
    V *hostMem_;
    cudaEvent_t evt_;
    QstateIdx ctxEnd_;
    QstateIdx curBegin_, curEnd_;
    QstateIdx stride_;
    int nCopyWorkers_;

    void setCtxSpan(QstateIdx ctxBegin, QstateIdx ctxEnd) {
        ctxEnd_ = ctxEnd;
        curBegin_ = ctxBegin;
        curEnd_ = std::min(ctxBegin + stride_, ctxEnd);
    }

    bool launch() {
        if (curBegin_ == ctxEnd_)
            return false;

        worker_->run(hostMem_, curBegin_, curEnd_);
        /* this works for flushing driver queue like cudaStreamQuery(). */
        throwOnError(cudaEventRecord(evt_));
        return true;
    }

    void syncAndCopy(V *values) const {
        throwOnError(cudaEventSynchronize(evt_));
        auto copyFunctor = [=](int threadIdx, QstateIdx spanBegin, QstateIdx spanEnd) {
            memcpy(&values[spanBegin], &hostMem_[spanBegin - curBegin_],
                   sizeof(V) * (spanEnd - spanBegin));
        };
        qgate::Parallel(nCopyWorkers_).distribute(copyFunctor, curBegin_, curEnd_);
    }

    void updateSpan() {
        curBegin_ = curEnd_;
        curEnd_ = std::min(curBegin_ + stride_, ctxEnd_);
    }
};

}

template<class V>
void qgate_cuda::run_d2h(V *array, DeviceWorkers &workers,
                         qgate::QstateIdx begin, qgate::QstateIdx end) {

    enum { nContextsPerWorker = 2, };

    typedef std::list<Context<V>*> Contexts;
    typedef std::vector<Contexts> ThreadContexts;
    ThreadContexts threadContexts(workers.size());

    size_t hMemCapacity = 1 << 30; /* a big value. */
    /* get min remaining capacity. */
    for (auto &worker : workers)
        hMemCapacity = std::min(hMemCapacity, worker->getDevice().tempHostMemory().template remaining<V>());
    /* adjust hMemAcapcity and ctxStride */
    hMemCapacity = std::min(hMemCapacity, size_t(32) * (1 << 20)); /* max 32 MB per context. */

    /* FIXME: Current design is for one worker for one device. Can be refactored by using partial circuit in future. */
    QstateSize span = end - begin;
    /* span for worker */
    QstateSize workerStride = qgate::divru(span, (int)workers.size());
    /* span for Context, n Contexts per Worker*/
    QstateSize ctxStride = qgate::divru(workerStride, nContextsPerWorker);
    /* span for one execution/transfer.  */
    QstateSize execStride = (hMemCapacity / sizeof(V)) / nContextsPerWorker;
    execStride = qgate::roundDown(execStride, (1 << 10)); /* round down to 1024. */
    /* allocate hostMem, size is execStrie. */
    size_t hMemCapacityPerContext = sizeof(V) * execStride;

    /* nCopyWorkers.  3GB/s / core.  4 workers is enough for 12 GB/sec. (observed PCIe BW) */
    int nCopyWorkers = qgate::Parallel::getDefaultNWorkers() / (int)workers.size();
    nCopyWorkers = std::min(nCopyWorkers, 4);

    for (int workerIdx = 0; workerIdx < (int)workers.size(); ++workerIdx) {
        DeviceWorker *worker = workers[workerIdx];
        CUDADevice &device = worker->getDevice();
        device.makeCurrent();
        /* memory store */
        SimpleMemoryStore &memStore = device.tempHostMemory();
        /* creating contexts */
        for (int ictx = 0; ictx < nContextsPerWorker; ++ictx) {
            cudaEvent_t evt;
            throwOnError(cudaEventCreate(&evt, cudaEventBlockingSync | cudaEventDisableTiming));
            V *hostMem = memStore.allocate<V>(hMemCapacityPerContext);
            auto *ctx = new Context<V>(worker, hostMem, evt, execStride, nCopyWorkers);
            /* set span */
            int spanIdx = nContextsPerWorker * workerIdx + ictx;
            QstateIdx ctxSpanBegin = std::min(ctxStride * spanIdx + begin, end);
            QstateIdx ctxSpanEnd = std::min(ctxSpanBegin + ctxStride, end);
            ctx->setCtxSpan(ctxSpanBegin, ctxSpanEnd);
            threadContexts[workerIdx].push_back(ctx);
        }
    }
#if 0
    memset(array, 0, sizeof(V) * (end - begin));
#endif
    auto queueRunner = [=, &threadContexts](int threadIdx) {
        Contexts &contexts = threadContexts[threadIdx];
        Contexts running;
        for (auto *ctx : contexts) {
            ctx->worker_->getDevice().makeCurrent();
            if (ctx->launch())
                running.push_back(ctx);
        }
        while (!running.empty()) {
            auto *ctx = running.front();
            running.pop_front();
            ctx->worker_->getDevice().makeCurrent();
            ctx->syncAndCopy(array);
            ctx->updateSpan();
            if (ctx->launch())
                running.push_back(ctx);
        }
    };
    qgate::Parallel((int)workers.size()).run(queueRunner);

    for (int threadIdx = 0; threadIdx < (int)threadContexts.size(); ++threadIdx) {
        auto &contexts = threadContexts[threadIdx];
        for (auto it = contexts.begin(); it != contexts.end(); ++it) {
            throwOnError(cudaEventDestroy((*it)->evt_));
            delete *it;
        }
    }
    threadContexts.clear();

    /* NOTE: allocated memory chunks are not released here. */
}


template void qgate_cuda::run_d2h<float>(float *, DeviceWorkers &, QstateIdx begin, QstateIdx end);
template void qgate_cuda::run_d2h<double>(double *, DeviceWorkers &, QstateIdx begin, QstateIdx end);
