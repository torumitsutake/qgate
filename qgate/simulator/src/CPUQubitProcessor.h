#pragma once

#include "Interfaces.h"


namespace qgate_cpu {

using qgate::ComplexType;
using qgate::Matrix2x2C64;
using qgate::QubitStates;
using qgate::QstateIdx;
using qgate::QstateSize;
using qgate::MathOp;
using qgate::QubitStatesList;

template<class real>
class CPUQubitStates;


template<class real>
class CPUQubitProcessor : public qgate::QubitProcessor {
    typedef ComplexType<real> Complex;
    typedef qgate::MatrixType<Complex, 2> Matrix2x2CR;
public:
    CPUQubitProcessor();
    ~CPUQubitProcessor();

    virtual void synchronize();

    virtual void reset();
    
    virtual void initializeQubitStates(qgate::QubitStates &qstates, int nLanes);
    
    virtual void resetQubitStates(qgate::QubitStates &qstates);

    virtual double calcProbability(const qgate::QubitStates &qstates, int localLane);

    virtual void join(qgate::QubitStates &qstates,
                      const QubitStatesList &qstatesList, int nNewLanes);
    
    virtual void decohere(int value, double prob, qgate::QubitStates &qstates, int localLane);
    
    virtual void decohereAndSeparate(int value, double prob,
                                     qgate::QubitStates &qstates0, qgate::QubitStates &qstates1,
                                     const qgate::QubitStates &qstates, int localLane);
    
    virtual void applyReset(QubitStates &qstates, int localLane);

    virtual void applyGate(const Matrix2x2C64 &mat, QubitStates &qstates, int localLane);

    virtual void applyControlledGate(const Matrix2x2C64 &mat, QubitStates &qstates,
                                     const qgate::IdList &localControlLanes, int localTargetLane);
    
private:
    template<class G>
    void run(int nLanes, int nInputBits,
             const qgate::IdList &bitShiftMap, const G &gatef);

    real _calcProbability(const CPUQubitStates<real> &qstates, int localLane);
    
    template<class R, class F>
    void qubitsGetValues(R *values, const F &func,
                         const qgate::IdList *laneTransTables, qgate::QstateIdx emptyLaneMask,
                         const QubitStatesList &qstatesList,
                         QstateSize nStates, QstateIdx begin, QstateIdx step);
};

}
