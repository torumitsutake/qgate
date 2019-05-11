import numbers
import functools

# FIMXE: implement dump.

#@functools.total_ordering
class Observation :
    def __init__(self, reflist, value, none_mask) :
        self._reflist = reflist
        self._value = value
        self._none_mask = none_mask

    def __int__(self) :
        return self._value

    @property
    def int(self) :
        return self._value

    def __call__(self, key) :
        if not key in self._reflist :
            raise RuntimeError('unknown ref, {}.'.format(key)) # ref is not in reflist.
        idx = self._reflist.index(key)
        bit = 1 << idx
        if (self._value & bit) != 0 :
            return 1
        return 0 if (self._none_mask & bit) == 0 else None

    def _compare_parameter_check(self, other) :
        if isinstance(other, numbers.Integral) :
            raise ValueError('To compare with integer, use int() or Observation.int property.')

    def __eq__(self, other) :
        self._compare_parameter_check(other)
        if not isinstance(other, Observation) :
            raise TypeError('comparison with Observation and {} not supported.'.format(type(other)))
        return (self._reflist == other._reflist) \
            and (self._value == other._value) and (self._none_mask == other._none_mask)

    def __lt__(self, other) :
        self._compare_parameter_check(other)
        return NotImplemented

class ObservationList :
    def __init__(self, reflist, values) :
        self._reflist = reflist
        self._values = values

    @property
    def intarray(self) :
        return self._values[0]
        
    def __getitem__(self, key) :
        return self._values[0][key]

    def __len__(self) :
        return len(self._values[0])

    def __iter__(self) :
        return Iterator(self._reflist, self._values)

    def __getitem__(self, key) :
        if isinstance(key, slice) :
            return ObservationList(self._reflist, self._values[:, key])
        return Observation(self._reflist, self._values[0][key], self._values[1][key])

    def __call__(self, ref) :
        if not ref in self._reflist :
            raise RuntimeError('unknown ref, {}.'.format(ref)) # ref is not in reflist.

        idx = self._reflist.index(ref)
        bit = 1 << idx
        values = [1 if (v & bit) != 0 else 0 for v in self._values[0]]
        nones = [None if (v & bit) != 0 else 0 for v in self._values[1]]
        extracted = [v if none is not None else None for v, none in zip(values, nones)]
        return extracted

    def histgram(self) :
        keys = set(self._values[0])
        kzerolist = [(key, 0) for key in keys]
        hist = dict(kzerolist)
        for value in self._values[0] :
            hist[value] += 1
        return ObservationHistgram(hist, len(self._reflist), len(self))

    class Iterator :
        def __init__(self, reflist, values) :
            self._reflist = reflist
            self._iter = iter(values.transpose())

        def __next__(self) :
            masked_value = next(self._iter)
            return Observation(self._reflist, *masked_value)
    
class ObservationHistgram :
    def __init__(self, hist, n_bits, n_samples) :
        self._hist = hist
        self._n_bits = n_bits
        self._n_samples = n_samples

    @property
    def n_samples(self) :
        return self._n_samples

    def __len__(self) :
        return len(self._hist)

    def __iter__(self) :
        return iter(self._hist)

    def __getitem__(self, key) :
        return self._hist.get(key, 0)

    def keys(self) :
        return self._hist.keys()

    def values(self) :
        return self._hist.values()

    def items(self) :
        return self._hist.items()
