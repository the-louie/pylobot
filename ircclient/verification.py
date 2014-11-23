from random import randrange
import time
import hashlib
import datetime
import operator


def create_verification_hash(votes):
    votedata = ""
    for k in sorted(votes.keys()):
        votedata += '['+str(k).lower()+str(votes[k])+']'
    print "(verify) *** VERIFICATION: '%s'" % (votedata)
    return hashlib.sha512(votedata + str(hashlib.sha512(votedata).digest())).hexdigest()

def verify_verifications(votes, vote_verifications, mynick):
    all_bots_verified = True
    for botnick in votes.keys():
        if botnick not in vote_verifications:
            all_bots_verified = False
            break

    if not all_bots_verified:
        return

    print "(verify) *** All bots verified"
    verifications = {}
    for botnick in vote_verifications.keys():
        vhash = vote_verifications[botnick]
        if vhash not in verifications:
            verifications[vhash] = 0
        verifications[vhash] += 1

    sorted_verifications = sorted(verifications.items(), key=operator.itemgetter(1))
    print "(verify) *** sorted verifications: %s" % (sorted_verifications)
    if vote_verifications[mynick] != sorted_verifications[-1][0]: # my vhash == most popular vhash
    	return False
    else
    	return True
