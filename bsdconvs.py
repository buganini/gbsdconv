from bsdconv import Bsdconv

class Bsdconvs(object):
	def __init__(self, conversion, train):
		cs=conversion.upper().strip(',:|;').split(';')
		self.failed=False
		self.conversions=[]
		self.evaluaters=[]
		self.trainer=None
		self.cache={}
		self.lastc=0
		self.cinfo=None
		self.tempfile=None
		done={}
		if train:
			self.tempfile=mktemp('/tmp/gbsdconv.score.XXXXXX')
			os.unlink(self.tempfile[1])
			self.trainer=Bsdconv('LOCALE:HALF:LOWER:ZH-FUZZY-TW:SCORE-TRAIN:NULL')
			self.trainer.ctl(CTL_ATTACH_SCORE, self.tempfile[0], 0)
		for c in cs:
			if c in done:
				continue
			done[c]=1
			c1=c.replace(':SCORE:',':')
			c2=c.replace(':SCORE:',':HALF:LOWER:ZH-FUZZY-TW:SCORE:COUNT:')
			h1=Bsdconv(c1)
			h2=Bsdconv(c2)
			if not h1 or not h2:
				self.errorstr=Bsdconv.error()
				self.failed=True
				self.conversions=[Bsdconv('BYTE:BYTE')]
			else:
				if train:
					h2.ctl(CTL_ATTACH_SCORE, self.tempfile[0], 0)
				self.conversions.append(h1)
				self.evaluaters.append(h2)

	def __bool__(self):
		return not self.failed

	def __nonzero__(self):
		return self.__bool__()

	def __str__(self):
		return ';'.join([x.split('"')[1] for x in [str(x) for x in self.conversions]])

	def weighted_score(self, i):
		ierr=i.get("IERR", 0)
		oerr=i.get("OERR", 0)
		score=i.get("SCORE", 0)
		count=i.get("COUNT", 0)
		if count==0:
			return 0
		return float(score - (ierr + oerr) * 10) / float(count)

	def score_train(self, s):
		if self.trainer:
			self.trainer.testconv(s)

	def score_clear(self):
		if self.trainer:
			self.tempfile=mktemp("/tmp/gbsdconv.score.XXXXXX")
			os.unlink(self.tempfile[1])
			self.trainer.ctl(CTL_ATTACH_SCORE, self.tempfile[0], 0)
			for c in self.evaluaters:
				c.ctl(CTL_ATTACH_SCORE, self.tempfile[0], 0)

	def conv(self, s):
		self.cinfo=None
		for k,c in enumerate(self.evaluaters):
			c.testconv(s)
			score=self.weighted_score(c.counter())
			if k==0:
				self.lastc=0
				max_score=score
			elif score>max_score:
				self.lastc=k
				max_score=score
		return self.conversions[self.lastc].conv(s)

	def conv_list(self, a):
		for k,c in enumerate(self.evaluaters):
			score=0
			for s in a:
				c.testconv(s)
				i=c.counter()
				score+=self.weighted_score(c.counter())
			if k==0:
				self.lastc=0
				max_score=score
			elif score>max_score:
				self.lastc=k
				max_score=score
		ret=[]
		for k,s in enumerate(a):
			ret.append(self.conversions[self.lastc].conv(s))
			if k==0:
				self.cinfo=self.conversions[self.lastc].counter()
			else:
				n=self.conversions[self.lastc].counter()
				self.cinfo={x:n[x]+self.cinfo[x] for x in n}
		return ret

	def conv_file(self, ifile, ofile):
		self.cinfo=None
		for k,c in enumerate(self.evaluaters):
			c.testconv_file(ifile)
			score=self.weighted_score(c.counter())
			if k==0:
				self.lastc=0
				max_score=score
			elif score>max_score:
				self.lastc=k
				max_score=score
		self.conversions[self.lastc].conv_file(ifile, ofile)
		return

	def testconv_file(self, str):
		for k,c in enumerate(self.evaluaters):
			c.testconv_file(str)
			score=self.weighted_score(c.counter())
			if k==0:
				self.lastc=0
				max_score=score
			elif score>max_score:
				self.lastc=k
				max_score=score
		self.cinfo=self.evaluaters[self.lastc].counter()
		return

	def counter(self):
		if self.cinfo:
			return self.cinfo
		return self.conversions[self.lastc].counter()

	def error(self):
		return self.errorstr
