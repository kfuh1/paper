"""
Customized checker for implementation following the same format
as simple_checker. Checks that I added have comment above or next
to the line of code with "kfuh". The function extra_test_recommendations
was added to do some extra testing for get_recommend_papers without
disturbing the existing tests from simple_checker

Name: Kathleen Fuh
AndrewID: kfuh
"""

# Import necessary packages
import paper.database_wrapper as db_wrapper
import paper.functions as funcs
from paper.constants import *

from datetime import datetime
from datetime import timedelta

"""
Test constants
"""

USERS = ["foo", "bar", "foofoo", "barbar", "foobar"]
TITLES = ["1", "2", "3", "4", "5"]
DESCS = ["This is just the desc1"]
TEXTS = ["I have an apple. I have a pen. --> ApplePen",
         "I have a pineapple. I have a pen. --> PineapplePen",
         "ApplePen. PineapplePen. --> PenPineappleApplePen",
         "Why this is popular?",
         "PPAP PPAP PPAP PPAP"]
TAGS = ["tag1", "tag2", "tag3", "tag4"]

ALL_FUNCS = ['add_new_paper', 'delete_paper', 'get_paper_tags',
             'get_papers_by_keyword', 'get_papers_by_tag',
             'get_papers_by_liked', 'get_most_active_users',
             'get_most_popular_papers', 'get_most_popular_tag_pairs',
             'get_most_popular_tags', 'get_number_papers_user', 'get_number_tags_user',
             'get_number_liked_user', 'get_recommend_papers', 'get_timeline',
             'get_timeline_all', 'get_likes', 'login', 'reset_db',
             'signup', 'unlike_paper', 'like_paper']
RES = {}
VERBOSE = False


def report_result():
    # Report result
    print "**********************************"
    print "*          TEST RESULTS          *"
    print "**********************************"
    pass_tests = []
    failed_tests = []
    not_tested = []
    for func_name in ALL_FUNCS:
        if func_name in RES:
            if RES[func_name] is True:
                pass_tests.append(func_name)
            else:
                failed_tests.append(func_name)
        else:
            not_tested.append(func_name)
    maxlen = len(max(ALL_FUNCS, key=len))
    for t in sorted(failed_tests, key=len):
        print "[%s]: Failed" % t.ljust(maxlen)
    for t in sorted(not_tested, key=len):
        print "[%s]: Not tested" % t.ljust(maxlen)
    for t in sorted(pass_tests, key=len):
        print "[%s]: Pass" % t.ljust(maxlen)


def exit_test():
    report_result()
    exit(1)


def error_message(func, msg, should_abort = True):
    RES[func.__name__] = False
    print "[Error in %s]: %s" % (func.__name__, msg)
    if should_abort:
        exit_test()


def format_error(func, should_abort = True):
    error_message(func, "incorrect return value format", should_abort)


def status_error(func, should_abort = True):
    error_message(func, "failed unexpectedly", should_abort)


def db_wrapper_debug(func, argdict, verbose = VERBOSE):
    if verbose:
        msg = "[Test] %s(" % func.__name__
        for k,v in argdict.iteritems():
            msg += " %s = %s," % (str(k), str(v))
        msg += " )"
        print msg
    res = db_wrapper.call_db(func, argdict)
    if verbose:
        print "\treturn: %s" % str(res)
    return res


# I'm calling this function at the end of main and resetting up the
# db with my own values so I don't run into problems with the existing
# tests from simple_checker
def extra_test_recommendations():
    users = ["a", "b", "c", "d", "e"]
    titles = ["1", "2", "3", "4", "5"]
    desc = ["This is just the desc1"]
    texts = ["hello world", "bonjour monde",
             "hello hello hello", "paper text world",
            "Bonjour Bonjour, monde"]
    tags = ["tag1", "tag2", "tag3", "tag4"]
    try:
        for user in USERS:
            status, res = db_wrapper_debug(funcs.signup, {'uname':user, 'pwd':user})
            if status != SUCCESS:
                status_error(funcs.signup)
    except TypeError:
        format_error(funcs.signup)
    pids = []
    try:
        tag_count = len(tags)
        # each user uploads one paper
        for pid in range(len(TITLES)):
            status, res = db_wrapper_debug(funcs.add_new_paper, {'uname':USERS[pid], 'title':TITLES[pid],
                                            'desc':DESCS[0], 'text':TEXTS[pid],
                                            'tags':[TAGS[pid % tag_count], TAGS[(pid+1) % tag_count], TAGS[(pid+2) % tag_count]]}
                                        )
            if status != SUCCESS:
                status_error(funcs.add_new_paper)
            else:
                test_pid = int(res)
                pids.append(test_pid)
    except TypeError:
        format_error(funcs.add_new_paper)
    try:
        # added like [4,4] - kfuh
        for likes in [[0,2], [0,3], [1,1], [1,3], [2,1], [2,4]]:
            status, res = db_wrapper_debug(funcs.like_paper, {'uname':USERS[likes[0]], 'pid':likes[1]})
            if status != SUCCESS:
                status_error(funcs.like_paper) 
    except TypeError:
        format_error(funcs.like_paper)
    try:
        # test that a person does not get recommended his own papers
        status, res = db_wrapper_debug(funcs.get_recommend_papers, {'uname':USERS[0]})
        if res != []:
            error_message(funcs.get_recommend_papers, "recommended papers incorrect") 
        # standard recommendation test
        status, res = db_wrapper_debug(funcs.get_recommend_papers, {'uname':USERS[1]})
        if res[0][0] != 4:
            error_message(funcs.get_recommend_papers, "recommended papers incorrect") 
    except TypeError:
        format_error(funcs.get_recommend_papers)


if __name__ == "__main__":
    # Reset the database
    RES[funcs.reset_db.__name__] = True
    try:
        status, res = db_wrapper_debug(funcs.reset_db, {})
        if status != SUCCESS:
            status_error(funcs.reset_db)

    except TypeError:
        format_error(funcs.reset_db)

    # Test signup
    RES[funcs.signup.__name__] = True
    try:
        for user in USERS:
            status, res = db_wrapper_debug(funcs.signup, {'uname':user, 'pwd':user})
            if status != SUCCESS:
                status_error(funcs.signup)
        # signup with an existing username - kfuh
        status, res = db_wrapper_debug(funcs.signup, {'uname':USERS[0], 'pwd':USERS[0]})
        if status != FAILURE:
            status_error(funcs.signup)
        # signup with username that's too long - kfuh
        long_uname = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        status, res = db_wrapper_debug(funcs.signup, {'uname':long_uname, 'pwd':'p'})
        if status != 2: # this is another case of failure not in constants
            status_error(funcs.signup)
        # signup with password that's too long - kfuh
        long_pwd = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        status, res = db_wrapper_debug(funcs.signup, {'uname':'a', 'pwd':long_pwd})
        if status != 2: # this is another case of failure not in constants
            status_error(funcs.signup)
    except TypeError:
        format_error(funcs.signup)

    # Test login
    RES[funcs.login.__name__] = True
    try:
        status, res = db_wrapper_debug(funcs.login, {'uname':USERS[0], 'pwd':USERS[0]})
        if status != SUCCESS:
            status_error(funcs.login,)
        # login with incorrect password
        status, res = db_wrapper_debug(funcs.login, {'uname':USERS[0], 'pwd':USERS[1]})
        if status == SUCCESS:
            error_message(funcs.login, "password is not matched but still return login success")
        # login with nonexistent username - kfuh
        status, res = db_wrapper_debug(funcs.login, {'uname':'a', 'pwd':USERS[0]})
        if status != 1:
            status_error(funcs.login)
    except TypeError:
        format_error(funcs.login,)

    # Test new papers
    RES[funcs.add_new_paper.__name__] = True
    pids = []
    try:
        tag_count = len(TAGS)
        for pid in range(len(TITLES)):
            status, res = db_wrapper_debug(funcs.add_new_paper, {'uname':USERS[0], 'title':TITLES[pid],
                                            'desc':DESCS[0], 'text':TEXTS[pid],
                                            'tags':[TAGS[pid % tag_count], TAGS[(pid+1) % tag_count], TAGS[(pid+2) % tag_count]]}
                                        )
            if status != SUCCESS:
                status_error(funcs.add_new_paper)
            else:
                test_pid = int(res)
                pids.append(test_pid)
        # new paper with title that's too long - kfuh
        long_title = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        status, res = db_wrapper_debug(funcs.add_new_paper, {'uname':USERS[0], 'title':long_title,
                                        'desc':DESCS[0], 'text':TEXTS[pid],
                                        'tags':[TAGS[pid % tag_count], TAGS[(pid+1) % tag_count], TAGS[(pid+2) % tag_count]]}
                                    )
        if status != FAILURE:
            status_error(funcs.add_new_paper)
        # new paper with a non alphanumeric tag - kfuh
        status, res = db_wrapper_debug(funcs.add_new_paper, {'uname':USERS[0], 'title':'title',
                                        'desc':DESCS[0], 'text':TEXTS[pid],
                                        'tags':['hello','tag,']}
                                    )
        if status != FAILURE:
            status_error(funcs.add_new_paper)
    except (TypeError, ValueError):
        format_error(funcs.add_new_paper)

    # Test like / unlike (successful unlike tested further below)
    RES[funcs.like_paper.__name__] = True
    try:
        # added like [4,4] - kfuh
        for likes in [[1, 1], [2, 1], [2, 2], [2, 3], [3, 1], [3, 3], [4,4]]:
            status, res = db_wrapper_debug(funcs.like_paper, {'uname':USERS[likes[0]], 'pid':likes[1]})
            if status != SUCCESS:
                status_error(funcs.like_paper)
        # user likes own paper - kfuh
        status, res = db_wrapper_debug(funcs.like_paper, {'uname':USERS[0], 'pid':1})
        if status != FAILURE:
            status_error(funcs.like_paper)
        # user tries to like paper twice - kfuh
        status, res = db_wrapper_debug(funcs.like_paper, {'uname':USERS[1], 'pid':1})
        if status != FAILURE:
            status_error(funcs.like_paper)
        # user tries to like nonexistent paper
        status, res = db_wrapper_debug(funcs.like_paper, {'uname':USERS[1], 'pid':8})
        if status != FAILURE:
            status_error(funcs.like_paper)
        # user tries to unlike paper he hasn't liked before - kfuh
        status, res = db_wrapper_debug(funcs.unlike_paper, {'uname':USERS[1], 'pid':4})
        if status != FAILURE:
            status_error(funcs.unlike_paper)
    except TypeError:
        format_error(funcs.like_paper)

    # Test list papers
    list_funcs_ctx = [
        (funcs.get_timeline, [5, 4, 3, 2, 1], {'uname':USERS[0]}),
        # timeline for user who hasn't uploaded anything - kfuh
        (funcs.get_timeline, [], {'uname':USERS[1]}),
        # timeline for nonexistent user - kfuh
        (funcs.get_timeline, [], {'uname':'blah'}),
        (funcs.get_timeline_all, [5, 4, 3, 2, 1], {}),
        # count is smaller than number of papers - kfuh
        (funcs.get_timeline_all, [5, 4, 3], {'count':3}),
        (funcs.get_papers_by_tag, [5, 4, 3, 1], {'tag':TAGS[0]}),
        # search by tag that doesn't exist - kfuh
        (funcs.get_papers_by_tag, [], {'tag':'tagggg'}),
        (funcs.get_papers_by_keyword, [2], {'keyword':'pineapple'}),
        # check result is case insensitive - kfuh
        (funcs.get_papers_by_keyword, [2,1], {'keyword':'Pen'}),
        # check search when keyword not in any text - kfuh
        (funcs.get_papers_by_keyword, [], {'keyword':'blah'}),
        (funcs.get_papers_by_liked, [1], {'uname':USERS[1]}),
        # get papers liked by nonexistent user - kfuh
        (funcs.get_papers_by_liked, [], {'uname':'user'}),
        (funcs.get_most_popular_papers, [1, 3, 2, 4], {'begin_time':datetime.now() + timedelta(days=-1)}),
        # begin_time is after all the papers have been uploaded - kfuh
        (funcs.get_most_popular_papers, [], {'begin_time':datetime.now()}),
        (funcs.get_recommend_papers, [3, 2], {'uname':USERS[1]}),
        #additional tests for recommend papers - kfuh
        (funcs.get_recommend_papers, [], {'uname':USERS[0]}),
        (funcs.get_recommend_papers, [], {'uname':USERS[4]}),
        (funcs.get_recommend_papers, [], {'uname':USERS[2]}),
        (funcs.get_recommend_papers, [2], {'uname':USERS[3]})
    ]

    for func, ans, args in list_funcs_ctx:
        RES[func.__name__] = True
        try:
            status, res = db_wrapper_debug(func, args)
            if status != SUCCESS:
                status_error(func,)
            else:
                pids_return = []
                for paper in res:
                    if len(paper) != 5:
                        raise TypeError("paper tuple length ts not 5")
                    else:
                        pids_return.append(paper[0])
                if pids_return != ans:
                    error_message(func, "expect pids %s but return %s" % (ans, pids_return))
        except (TypeError, ValueError):
                format_error(func)

    # Test directly test return values
    value_func_ctx = [
        (funcs.get_likes, 3, {'pid':1}),
        (funcs.get_likes, 1, {'pid':4}), # additional success case test - kfuh
        (funcs.get_likes, 0, {'pid':5}), # get count of likes for paper with none - kfuh
        (funcs.get_likes, 0, {'pid':10}), # nonexistent pid - kfuh
        (funcs.get_most_active_users, [USERS[0]], {'count':1}),
        # more counts than people who have uploaded papers - kfuh
        (funcs.get_most_active_users, [USERS[0]], {'count':3}), 
        (funcs.get_most_popular_tags, [(TAGS[0], 4)], {'count':1}),
        # count > 1 and tags in need of tiebreaker
        (funcs.get_most_popular_tags, [(TAGS[0], 4), (TAGS[1], 4)], {'count':2}),
        (funcs.get_most_popular_tag_pairs, [(TAGS[0], TAGS[1], 3)], {'count':1}),
        (funcs.get_number_papers_user, 5, {'uname':USERS[0]}),
        # get number of papers for user with none - kfuh
        (funcs.get_number_papers_user, 0, {'uname':USERS[1]}),
        # get number of paper for invalid user - kfuh
        (funcs.get_number_papers_user, 0, {'uname':'blah'}),
        (funcs.get_number_tags_user, 4, {'uname':USERS[0]}),
        # get number of tags for invalid user - kfuh
        (funcs.get_number_tags_user, 0, {'uname':'blah'}),
        # get number of tags for user who hasn't uploaded papers - kfuh
        (funcs.get_number_tags_user, 0, {'uname':USERS[1]}),
        (funcs.get_number_liked_user, 3, {'uname':USERS[2]}),
        # nonexistent user - kfuh
        (funcs.get_number_liked_user, 0, {'uname':'blah'}),
        (funcs.get_paper_tags, ['tag1', 'tag2', 'tag3'], {'pid':1}),
        # nonexistent paper id - kfuh
        (funcs.get_paper_tags, [], {'pid':10}),
        
    ]

    for func, ans, args in value_func_ctx:
        RES[func.__name__] = True
        try:
            status, res = db_wrapper_debug(func, args)
            if status != SUCCESS:
                status_error(funcs,)
            else:
                if ans != res:
                    error_message(func, "expect %s but return %s" % (ans, res))
        except (TypeError, ValueError):
            format_error(func)

    # Test functions with no return value
    none_func_ctx = [
        (funcs.unlike_paper, {'uname':USERS[1], 'pid':1}),
        (funcs.delete_paper, {'pid':1}),
    ]

    for func, args in none_func_ctx:
        RES[func.__name__] = True
        try:
            status, res = db_wrapper_debug(func, args)
            if status != SUCCESS:
                status_error(func,)
        except (TypeError, ValueError):
            format_error(func)

    # Reset database
    db_wrapper_debug(funcs.reset_db, {})
    
    # kfuh - additional testing requiring clean db
    extra_test_recommendations()
    
    db_wrapper_debug(funcs.reset_db, {})
    report_result()
