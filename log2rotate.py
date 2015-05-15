import argparse
import datetime
from math import log
import sys

def backups_to_keep(n):
	if n == 0:
		return set()
	elif n == 1:
		return set([1])
	else:
		return set([n]) | backups_to_keep(n - 2**(int(log(n, 2)) - 1))

class Log2RotateUnsafeError(ValueError): pass

class Log2Rotate(object):
	def backups_to_keep(self, state, unsafe=False, fuzz=0):
		state_sorted = sorted(state, cmp=self.cmp)

		if len(state_sorted) < 2:
			return state_sorted
		else:
			last = state_sorted[-1]
			first = state_sorted[0]

			n0_to_b = dict((self.sub(last, b) + 1, b) for b in state)
			n = self.sub(last, first) + 1

			r = backups_to_keep(n)

			new_state = []
			for n0 in sorted(r, reverse=True):
				for m in range(fuzz+1):
					if n0+m in n0_to_b:
						b = n0_to_b[n0+m]
						new_state.append(b)
						break
				else:
					if not unsafe:
						raise Log2RotateUnsafeError

			return new_state

	def cmp(self, x, y):
		return cmp(x, y)

	def sub(self, x, y):
		return x - y

class Log2RotateStr(Log2Rotate):

	def __init__(self, fmt):
		self.fmt = fmt

	def strptime(self, s):
		return datetime.datetime.strptime(s, self.fmt)

	def cmp(self, x, y):
		x2 = self.strptime(x)
		y2 = self.strptime(y)

		return cmp(x2, y2)

	def sub(self, x, y):
		x2 = self.strptime(x)
		y2 = self.strptime(y)

		return (x2 - y2).days

def run(args, inp):

	l2r = Log2RotateStr(args.fmt)

	inp_orig = set(inp)

	# filter out all lines that do not conform to format
	# we always want to keep these.
	def parseable(s):
		try:
			l2r.strptime(s)
		except ValueError:
			return False
		else:
			return True

	inp = filter(parseable, inp)
	out = list(inp_orig - set(inp))
	if out:
		sys.stderr.write("warning: keeping %d backups with unparseable names\n" % (len(out,)))

	# sort input list of backups. oldest backups first.
	inp.sort(cmp=l2r.cmp)

	# if we are skipping some of the latest backups,
	# put them directly into the list of backups to keep
	# and remove them from input list for the log2rotate
	# algorithm.
	if args.skip > 0:
		out += inp[-args.skip:]
		inp = inp[:-args.skip]

	# if there are any backups left that need to be rotated,
	# run them through log2rotate and append the result to
	# the list of backups to keep.
	if inp:
		out += l2r.backups_to_keep(inp, unsafe=args.unsafe)

	if args.show_keep:
		return out
	else:
		return inp_orig - set(out)

def main():
	parser = argparse.ArgumentParser(description="rotate backups using exponentially-growing periods.")

	parser.add_argument('-d', '--delete', action='store_true', dest='show_delete',
			help="show backups to delete")
	parser.add_argument('-k', '--keep', action='store_true', dest='show_keep',
			help="show backups to keep")
	parser.add_argument('-u', '--unsafe', action='store_true', dest='unsafe',
			help="make unsafe recommendations")
	parser.add_argument('-s', '--skip', metavar='NUM', type=int, dest='skip', default=0,
			help="always keep NUM latest backups")
	parser.add_argument('-f', '--format', metavar='FMT', dest='fmt', default="%Y-%m-%d",
			help="use FMT for parsing date from backup name")

	args = parser.parse_args()

	if (not args.show_keep and not args.show_delete) or (args.show_keep and args.show_delete):
		sys.stderr.write("error: please specify either --keep or --delete\n")
		sys.exit(1)

	inp = [ line.strip() for line in sys.stdin ]

	try:
		out = run(args, inp)
	except Log2RotateUnsafeError:
		sys.stderr.write("error: backups that should have been kept are missing from the input list (use --unsafe to proceed anyway)\n")
	else:
		for line in out:
			print line

if __name__ == '__main__':
	main()
