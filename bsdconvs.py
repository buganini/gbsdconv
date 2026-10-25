"""UI-independent conversion selection and score training."""
import math
import os
import tempfile
from collections import Counter
from contextlib import contextmanager

from bsdconv import Bsdconv


@contextmanager
def score_environment(filename):
    previous = os.environ.get('BSDCONV_SCORE')
    os.environ['BSDCONV_SCORE'] = filename
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('BSDCONV_SCORE', None)
        else:
            os.environ['BSDCONV_SCORE'] = previous


class Bsdconvs:
    def __init__(self, conversion, train=False, factors=(-10.0, -10.0, 1.0)):
        self.specs = list(dict.fromkeys(c.strip().upper() for c in conversion.split(';') if c.strip()))
        if not self.specs:
            raise ValueError('Enter a conversion, for example UTF-8:UTF-8.')
        self.factors = tuple(float(v) for v in factors)
        if len(self.factors) != 3 or not all(math.isfinite(value) for value in self.factors):
            raise ValueError('Scoring weights must be three finite numbers.')
        self.conversions = []
        self.evaluaters = []
        self.trainer = None
        self.tempfile = None
        self._tempdir = None
        self.lastc = 0
        self.cinfo = {}
        self.failed = False
        self.errorstr = ''
        try:
            if train:
                self._tempdir = tempfile.TemporaryDirectory(prefix='gbsdconv-score-')
                self.score_path = os.path.join(self._tempdir.name, 'scores')
                self.tempfile = open(self.score_path, 'w+b')
                with score_environment(self.score_path):
                    self.trainer = self._create('UTF-8:HALF:LOWER:ZH-FUZZY-TW:SCORE-TRAIN:NULL')
                self.trainer.ctl(Bsdconv.CTL_ATTACH_SCORE, self.tempfile, 0)
            for spec in self.specs:
                output = spec.replace(':SCORE:', ':')
                scoring = 'SCORE#WITH=TRAINED' if train else 'SCORE'
                evaluation = spec.replace(':SCORE:', ':HALF:LOWER:ZH-FUZZY-TW:' + scoring + ':COUNT:')
                if train:
                    with score_environment(self.score_path):
                        evaluator = self._create(evaluation)
                    evaluator.ctl(Bsdconv.CTL_ATTACH_SCORE, self.tempfile, 0)
                else:
                    evaluator = self._create(evaluation)
                self.conversions.append(self._create(output))
                self.evaluaters.append(evaluator)
        except Exception:
            self.close()
            raise

    @staticmethod
    def _create(spec):
        converter = Bsdconv(spec)
        if not converter:
            raise ValueError(f'{spec}: {Bsdconv.error()}')
        return converter

    def __bool__(self):
        return True

    def __str__(self):
        return ';'.join(self.specs)

    def close(self):
        self.conversions.clear()
        self.evaluaters.clear()
        self.trainer = None
        if self.tempfile is not None:
            self.tempfile.close()
            self.tempfile = None
        if self._tempdir is not None:
            self._tempdir.cleanup()
            self._tempdir = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def weighted_score(self, counters):
        ierr, oerr, score = self.factors
        return (ierr * counters.get('IERR', 0) + oerr * counters.get('OERR', 0)
                + score * counters.get('SCORE', 0)) / max(counters.get('COUNT', 0), 1)

    def score_train(self, value):
        if self.trainer:
            self.trainer.testconv(value)

    def score_clear(self):
        if self.tempfile is not None:
            self.tempfile.seek(0)
            self.tempfile.truncate()
            self.tempfile.flush()
            self.trainer.init()

    def _choose(self, values):
        scores = []
        for evaluator in self.evaluaters:
            counters = Counter()
            for value in values:
                evaluator.testconv(value)
                counters.update(evaluator.counter())
            scores.append(self.weighted_score(counters))
        self.lastc = max(range(len(scores)), key=scores.__getitem__)
        return self.conversions[self.lastc]

    def conv(self, value):
        converter = self._choose([value])
        result = converter.conv(value)
        self.cinfo = converter.counter()
        return result

    def conv_list(self, values):
        converter = self._choose(values)
        result, counters = [], Counter()
        for value in values:
            result.append(converter.conv(value))
            counters.update(converter.counter())
        self.cinfo = dict(counters)
        return result

    def select_file(self, filename):
        scores = []
        for evaluator in self.evaluaters:
            evaluator.init()
            with open(filename, 'rb') as source:
                while chunk := source.read(65536):
                    evaluator.conv_chunk(chunk)
            evaluator.conv_chunk_last(b'')
            scores.append(self.weighted_score(evaluator.counter()))
        self.lastc = max(range(len(scores)), key=scores.__getitem__)
        return self.conversions[self.lastc]

    def convert_stream(self, source, target, converter):
        converter.init()
        while chunk := source.read(65536):
            target.write(converter.conv_chunk(chunk))
        target.write(converter.conv_chunk_last(b''))
        self.cinfo = converter.counter()

    def conv_file(self, ifile, ofile):
        converter = self.select_file(ifile)
        with open(ifile, 'rb') as source, open(ofile, 'wb') as target:
            self.convert_stream(source, target, converter)

    def testconv_file(self, filename):
        converter = self.select_file(filename)
        converter.init()
        with open(filename, 'rb') as source:
            while chunk := source.read(65536):
                converter.conv_chunk(chunk)
        converter.conv_chunk_last(b'')
        self.cinfo = converter.counter()

    def counter(self):
        return self.cinfo

    def error(self):
        return self.errorstr
