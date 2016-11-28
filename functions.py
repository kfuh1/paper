"""
Name: Kathleen Fuh
AndrewID: kfuh
"""

import psycopg2 as psy

from datetime import datetime
from pytz import timezone
from constants import *

"""
General rules:
    (1) How will the WebApp call these APIs?
    Say we have an API foo(...) defined in this file. The upper layer Application
    will invoke these API through a wrapper in the following way:

    database_wrapper(...):
        conn = None
        try:
            conn = psycopg2.connection()
            res = foo(conn, ...)
            return res
        except psycopg2.DatabaseError, e:
            print "Error %s: " % e.argsp[0]
            conn.rollback()
            return DB_ERROR, None
        finally:
            if conn:
                conn.close()

    So, you don't need to care about the establishment and termination of
    the database connection, we will pass it as a parameter to the api.

    (2) General pattern for return value.
    Return value of every API defined here is a two element tuples (status, res).
    Status indicates whether the API call is success or not. Status = 0 means success,
    otherwise the web app will identify the error type by the value of the status.

    Res is the actual return value from the API. If the API has no return value, it should be
    set to None. Otherwise it could be any python data structures or primitives.
"""


def example_select_current_time(conn):
    """
    Example: Get current timestamp from the database

    :param conn: A postgres database connection object
    :return: (status, retval)
        (0, dt)     Success, retval is a python datetime object
        (1, None)           Failure
    """
    try:
        # establish a cursor
        cur = conn.cursor()
        # execute a query
        cur.execute("SELECT localtimestamp")
        # get back result tuple
        res = cur.fetchone()
        # extract the result as a datetime object
        dt = res[0]
        # return the status and result
        return 0, dt
    except psy.DatabaseError, e:
        # catch any database exception and return failure status
        return 1, None


# Admin APIs


def reset_db(conn):
    """
    Reset the entire database.
    Delete all tables and then recreate them.

    :param conn: A postgres database connection object
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    commands = (
        """
        DROP TABLE IF EXISTS tags, tagnames, likes, papers, users
        """,
        """
        CREATE TABLE IF NOT EXISTS users(
            username VARCHAR(50) NOT NULL,
            password VARCHAR(32) NOT NULL,
            PRIMARY KEY(username)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS papers(
            pid  SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            title VARCHAR(50),
            begin_time TIMESTAMP NOT NULL,
            description VARCHAR(500),
            data TEXT,
            FOREIGN KEY(username) REFERENCES users ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX paper_text_idx ON papers USING gin(to_tsvector('english', data))
        """,
        """
        CREATE TABLE IF NOT EXISTS tagnames(
            tagname VARCHAR(50) NOT NULL,
            PRIMARY KEY(tagname)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS likes(
            pid INT NOT NULL,
            username VARCHAR(50) NOT NULL,
            like_time TIMESTAMP NOT NULL,
            PRIMARY KEY(pid, username),
            FOREIGN KEY(pid) REFERENCES papers ON DELETE CASCADE,
            FOREIGN KEY(username) REFERENCES users ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS tags(
            pid INT NOT NULL,
            tagname VARCHAR(50) NOT NULL,
            PRIMARY KEY(pid, tagname),
            FOREIGN KEY(pid) REFERENCES papers ON DELETE CASCADE,
            FOREIGN KEY(tagname) REFERENCES tagnames ON DELETE CASCADE
        );
        """,
    )
    cur = conn.cursor()
    for command in commands:
        cur.execute(command)
    conn.commit()
    return 0, None

# Basic APIs


def signup(conn, uname, pwd):
    """
    Register a user with a username and password.
    This function first check whether the username is used. If not, it
    registers the user in the users table.

    :param conn:  A postgres database connection object
    :param uname: A string of username
    :param pwd: A string of user's password
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure -- Username is used
        (2, None)   Failure -- Other errors
    """
    # (kfuh)
    try:
        cur = conn.cursor()
        # check if username already exists
        sql = "SELECT COUNT(*) FROM users WHERE username = %s;"
        data = (uname,)
        cur.execute(sql, data)
        count = cur.fetchone()
        if count[0] > 0:
            return 1, None

        sql = "INSERT INTO users VALUES(%s,%s);"
        data = (uname, pwd,)
        cur.execute(sql, data)
    
        conn.commit()
        # one row was affected which means successful insert
        if cur.rowcount == 1:
            return 0, None
        # since we already checked for existing user at this point
        # unsuccessful insert is another error
        else:
            return 2, None
    except psy.DatabaseError, e:
        return 2, None


def login(conn, uname, pwd):
    """
    Login if user and password match.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param pwd: A string of user's password
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure -- User does not exist
        (2, None)   Failure -- Password incorrect
        (3, None)   Failure -- Other errors
    """
    # (kfuh)
    try:
        cur = conn.cursor()
        sql = "SELECT COUNT(*) FROM users WHERE username = %s AND password = %s;"
        data = (uname, pwd,)
        cur.execute(sql, data)
        count = cur.fetchone()[0]
        if count == 1:
            return 0, None
        # check reason for failure
        else:
            sql = "SELECT COUNT(*) FROM users WHERE username = %s;"
            data = (uname,)
            cur.execute(sql, data)
            user_count = cur.fetchone()[0]
            # user did not exist
            if user_count == 0:
                return 1, None
            else:
                sql = "SELECT password FROM users WHERE username = %s;"
                data = (uname,)
                cur.execute(sql, data)
                # must not None from fetchone bc at this point we know user exists
                password = cur.fetchone()[0]
                if password != pwd:
                    return 2, None
                else:
                    return 3, None
    except psy.DatabaseError, e:
        return 3, None


# Event related


def add_new_paper(conn, uname, title, desc, text, tags):
    """
    Create a new paper with  tags.
    Note that this API should touch multiple tables.
    Make sure you define a transaction properly. Also, don't forget to set the begin_time
    of the paper as current time.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param title: A string of the title of the paper
    :param desc: A string of the description of the paper
    :param text: A string of the text content of the uploaded pdf file
    :param tags: A list of string, each element is a tag associate to the paper
    :return: (status, retval)
        (0, pid)    Success
                    Return the pid of the newly inserted paper in the res field of the return value
        (1, None)   Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        time = datetime.now(timezone('US/Eastern'))
        sql =  "INSERT INTO papers(username, title, begin_time, description, data) \
            VALUES(%s, %s, %s, %s, %s) RETURNING pid;"
        data = (uname, title, str(time), desc, text,)
        cur.execute(sql, data)
        pid_db = cur.fetchone()
        # something went wrong with insert and no pid was returned
        # should be caught by a database exception, but this is just in case
        # there's some other case where this could happen
        if pid_db is None:
            return 1, None
        pid = pid_db[0]
        for t in tags:
            if not t.isalnum():
                return 1, None
            sql = "SELECT COUNT(*) FROM tagnames WHERE tagname = %s"
            data = (t,)
            cur.execute(sql, data)
            t_count = cur.fetchone()[0]
            if t_count == 0:
                sql = "INSERT INTO tagnames VALUES(%s);"
                data = (t,)
                cur.execute(sql, data)
            sql = "INSERT INTO tags VALUES(%s, %s);"
            data = (pid, t,)
            cur.execute(sql, data)
        # once everything has been inserted commit so full insertion is atomic
        conn.commit()
        return 0, pid
    except psy.DatabaseError, e:
        # something went wrong so rollback
        conn.rollback()
        return 1, None


def delete_paper(conn, pid):
    """
    Delete a paper by the given pid.

    :param conn: A postgres database connection object
    :param pid: An int of pid
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    try:
        cur = conn.cursor()
        sql = "DELETE FROM papers WHERE pid = %s;"
        data = (pid,)
        cur.execute(sql, data)
        conn.commit()
        return 0, None
    except psy.DatabaseError, e:
        print "delete_paper"
        print e
        return 1, None


def get_paper_tags(conn, pid):
    """
    Get all tags of a paper

    :param conn: A postgres database connection object
    :param pid: An int of pid
    :return: (status, retval)
        (0, [tag1, tag2, ...])      Success
                                    Return a list of string. Each string is a tag of the paper.
                                    Note that the list should be sorted in a lexical ascending order.
                                    Example:
                                            (0, ["database", "multi-versioned"])

        (1, None)                   Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT tagname FROM tags WHERE pid = %s"
        data = (pid,)
        cur.execute(sql, data)
        tags_db = cur.fetchall()
        tags = []
        # tags_db is a list of tuples so get the tags out of the tuples
        for t in tags_db:
            tags.append(t[0])
        return 0, tags
    except psy.DatabaseError, e:
        return 1, None

# Vote related


def like_paper(conn, uname, pid):
    """
    Record a like for a paper. Timestamped the like with the current timestamp

    You need to ensure that (1) a user should not like his/her own paper, (2) a user can not like a paper twice.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param pid: An int of pid
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT username FROM papers WHERE pid = %s;"
        data = (pid,)
        cur.execute(sql, data)
        paper_author_db = cur.fetchone()
        # invalid pid
        if paper_author_db is None:
            return 1, None
        paper_author = paper_author_db[0]
        # user can't like his/her own paper
        if paper_author == uname:
            return 1, None
        time = datetime.now(timezone('US/Eastern'))
        sql = "INSERT INTO likes VALUES(%s, %s, TIMESTAMP %s);"
        data = (pid, uname, str(time),)
        cur.execute(sql, data)
        conn.commit()
        # successful insert (i.e. valid like)
        if cur.rowcount == 1:
            return 0, None
        # unsuccessful insert because user has liked this paper before
        else:
            return 1, None
    except psy.DatabaseError, e:
        return 1, None


def unlike_paper(conn, uname, pid):
    """
    Record an unlike for a paper

    You need to ensure that the user calling unlike has liked the paper before

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param pid: An int of pid
    :return: (status, retval)
        (0, None)   Success
        (1, None)   Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "DELETE FROM likes WHERE pid = %s AND username = %s"
        data = (pid, uname,)
        cur.execute(sql, data)
        conn.commit()
        # successful unlike
        if cur.rowcount == 1:
            return 0, None
        else:
            return 1, None
    except psy.DatabaseError, e:
        return 1, None


def get_likes(conn, pid):
    """
    Get the number of likes of a paper

    :param conn: A postgres database connection object
    :param pid: An int of pid
    :return: (status, retval)
        (0, like_count)     Success, retval should be an integer of like count
        (1, None)           Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT COUNT(*) FROM likes WHERE pid = %s"
        data = (pid,)
        cur.execute(sql, data)
        like_count = cur.fetchone()[0]
        return 0, like_count
    except psy.DatabaseError, e:
        return 1, None

# Search related


def get_timeline(conn, uname, count = 10):
    """
    Get timeline of a user.

    You should return $count most recent posts of a user. The result should be ordered first by time (newest first)
    and then break ties by pid (ascending).

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param count: An int indicating the maximum number of papers you can return
    :return: (status, retval)
        (0, [(pid, username, title, begin_time, description), (...), ...])
          Success, retval is a list of quintuple. Each element of the quintuple is of the following type:
            pid --  Integer
            username, title, description -- String
            begin_time  -- A datetime.datetime object
            For example, the return value could be:
            (
                0,
                [
                    (1, "Alice", "title", begin_time, "description")),
                    (2, "Alice", "title2", begin_time2, "description2"))
                ]
            )


        (1, None)
            Failure
    """
    try:
        cur = conn.cursor()
        sql = "SELECT pid, username, title, begin_time, description FROM papers \
            WHERE username = %s ORDER BY begin_time DESC, pid LIMIT %s;"
        data = (uname, count,)
        cur.execute(sql, data)
        papers = cur.fetchall()
        return 0, papers
    except psy.DatabaseError, e:
        return 1, None


def get_timeline_all(conn, count = 10):
    """
    Get at most $count recent papers

    The results should be ordered by begin_time (newest first). Break ties by pid.

    :param conn: A postgres database connection object
    :param count: An int indicating the maximum number of papers you can return
    :return: (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT pid, username, title, begin_time, description FROM papers \
            ORDER BY begin_time DESC LIMIT %s;"
        data = (count,)
        cur.execute(sql, data)
        papers = cur.fetchall()
        return 0, papers
    except psy.DatabaseError, e:
        return 1, None


def get_most_popular_papers(conn, begin_time, count = 10):
    """
    Get at most $count papers posted after $begin_time according that have the most likes.

    You should order papers first by number of likes (descending) and break ties by pid (ascending).
    Also, paper with 0 like should not be listed here.

    :param conn: A postgres database connection object
    :param begin_time: A datetime.datetime object
    :param count:   An integer
    :return: (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    # kfuh - note we don't want 0 liked papers here
    try:
        cur = conn.cursor()
        sql = "WITH LikeCount AS ( \
            SELECT pid, COUNT(*) AS count FROM likes GROUP BY pid) \
            SELECT p.pid, p.username, title, begin_time, description \
                FROM papers p INNER JOIN LikeCount l \
                    ON p.pid = l.pid \
                WHERE begin_time > TIMESTAMP %s \
                ORDER BY l.count DESC, p.pid ASC \
                LIMIT %s;"
        data = (str(begin_time), count,)
        cur.execute(sql, data)
        papers = cur.fetchall()
        return 0, papers
    except psy.DatabaseError, e:
        return 1, None


def get_recommend_papers(conn, uname, count = 10):
    """
    Recommended at most $count papers for a user.

    Check T.15 in the project writeup for detailed description of this API.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param count:   An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    try:
        cur = conn.cursor()
        # Cohorts are people who like the same papers
        sql = "WITH Cohort AS ( \
            SELECT l1.pid, l2.username FROM likes l1 INNER JOIN likes l2 \
                ON l1.username = %s AND l1.username != l2.username AND l1.pid = l2.pid) \
            SELECT p.pid, p.username, title, begin_time, description \
                FROM papers p INNER JOIN ( \
                    SELECT pid, COUNT(*) AS count FROM likes \
                        WHERE pid NOT IN (SELECT pid FROM Cohort) \
                            AND username IN (SELECT username FROM Cohort) \
                        GROUP BY pid LIMIT %s) c ON p.pid = c.pid \
                        WHERE p.username != %s \
                        ORDER BY c.count DESC, p.pid;"
        data = (uname, count, uname,)
        cur.execute(sql, data)
        papers = cur.fetchall()
        return 0, papers
    except psy.DatabaseError, e:
        return 1, None


def get_papers_by_tag(conn, tag, count = 10):
    """
    Get at most $count papers that have the given tag

    The result should first be ordered by begin time (newest first). Break ties by pid (ascending).

    :param conn: A postgres database connection object
    :param tag: A string of tag
    :param count: An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT p.pid, p.username, title, begin_time, description \
            FROM papers p INNER JOIN tags t ON p.pid = t.pid \
            WHERE t.tagname = %s ORDER BY begin_time DESC, p.pid ASC \
            LIMIT %s"
        data = (tag, count,)
        cur.execute(sql, data)
        papers = cur.fetchall()
        return 0, papers
    except psy.DatabaseError, e:
        return 1, None


def get_papers_by_keyword(conn, keyword, count = 10):
    """
    Get at most $count papers that match a keyword in its title, description *or* text field

    The result should first be ordered by begin time (newest first). Break ties by pid (ascending).

    :param conn: A postgres database connection object
    :param keyword: A string of keyword, e.g. "database"
    :param count: An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT pid, username, title, begin_time, description \
            FROM papers WHERE title @@ to_tsquery(%s) OR \
            description @@ to_tsquery(%s) OR data @@ to_tsquery(%s) \
            ORDER BY begin_time DESC, pid ASC LIMIT %s;"
        data = (keyword, keyword, keyword, count,)
        cur.execute(sql, data)
        papers = cur.fetchall()
        return 0, papers
    except psy.DatabaseError, e:
        return 1, None


def get_papers_by_liked(conn, uname, count = 10):
    """
    Get at most $count papers that liked by the given user.

    The result should first be ordered by the time the like is made (newest first). Break ties by pid (ascending).

    :param conn: A postgres database connection object
    :param uname: A string of username
    :param count: An integer
    :return:    (status, retval)
        (0, [pid, username, title, begin_time, description), (...), ...])
            Success, retval is a list of quintuple. Please refer to the format defined in get_timeline()'s return value

        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        # l.username because we want papers liked by the user
        sql = "SELECT p.pid, p.username, title, begin_time, description \
            FROM papers p INNER JOIN likes l ON p.pid = l.pid  \
            WHERE l.username = %s ORDER BY like_time DESC, pid ASC \
            LIMIT %s;"
        data = (uname, count,)
        cur.execute(sql, data)
        papers = cur.fetchall()
        return 0, papers
    except psy.DatabaseError, e:
        return 1, None


# Statistics related


def get_most_active_users(conn, count = 1):
    """
    Get at most $count users that post most papers.

    The result should first be ordered by number of papers posted by the user. Break ties by username (lexically
    ascending). User that never posted papers should not be listed.

    :param conn: A postgres database connection object
    :param count: An integer
    :return: (status, retval)
        (0, [uname1, uname2, ...])
            Success, retval is a list of username. Each element in the list is a string. Return empty list if no
            username found.
        (1, None)
            Failure
    """
    try:
        cur = conn.cursor()
        sql = "SELECT username, COUNT(*) AS count FROM papers \
            GROUP BY username ORDER BY count DESC, username ASC \
            LIMIT %s;"
        data = (count,)
        cur.execute(sql, data)
        user_counts = cur.fetchall()
        users = []
        for u in user_counts:
            users.append(u[0])
        return 0, users 
    except psy.DatabaseError, e:
        return 1, None


def get_most_popular_tags(conn, count = 1):
    """
    Get at most $count many tags that gets most used among all papers

    The result should first be ordered by number of papers that has the tags. Break ties by tag name (lexically
    ascending).

    :param conn: A postgres database connection object
    :param count: An integer
    :return:
        (0, [(tagname1, count1), (tagname2, count2), ...])
            Success, retval is a list of tagname. Each element is a pair where the first component is the tagname
            and the second one is its count
        (1, None)
            Failure
    """
    # TODO: when displayed on site, it's a unicode string (u't1', 1L)
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT tagname, COUNT(*) AS count \
            FROM tags GROUP BY tagname ORDER BY count DESC, tagname ASC \
            LIMIT %s;"
        data = (count,)
        cur.execute(sql, data)
        tags = cur.fetchall()
        return 0, tags
    except psy.DatabaseError, e:
        return 1, None


def get_most_popular_tag_pairs(conn, count = 1):
    """
    Get at most $count many tag pairs that have been used together.

    You should avoid duplicate pairs like (foo, bar) and (bar, foo). They should only be counted once with lexical
    order. Results should first be ordered by number occurrences in papers. Break ties by tag name (lexically
    ascending).

    :param conn: A postgres database connection object
    :param count: An integer
    :return:
        (0, [(tag11, tag12, count), (tag21, tag22, count), (...), ...])
            Success, retval is a list of three-tuples. The elements of the three-tuple are two strings and a count.

        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT t1.tagname, t2.tagname, COUNT(*) AS count \
            FROM tags t1 INNER JOIN tags t2 \
            ON t1.pid = t2.pid AND t1.tagname < t2.tagname \
            GROUP BY t1.tagname, t2.tagname \
            ORDER BY count DESC, t1.tagname ASC, t2.tagname ASC \
            LIMIT %s;"
        data = (count,)
        cur.execute(sql, data)
        pairs = cur.fetchall()
        return 0, pairs
    except psy.DatabaseError, e:
        return 1, None


def get_number_papers_user(conn, uname):
    """
    Get the number of papers posted by a given user.

    :param conn: A postgres database connection object
    :param uname: A string of username
    :return:
        (0, count)
            Success, retval is an integer indicating the number papers posted by the user
        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT COUNT(*) FROM papers WHERE username = %s;"
        data = (uname,)
        cur.execute(sql, data)
        count = cur.fetchone()[0]
        return 0, count
    except psy.DatabaseError, e:
        return 1, None


def get_number_liked_user(conn, uname):
    """
    Get the number of likes liked by the user

    :param conn: A postgres database connection object
    :param uname:   A string of username
    :return:
        (0, count)
            Success, retval is an integer indicating the number of likes liked by the user
        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT COUNT(*) FROM likes WHERE username = %s;"
        data = (uname,)
        cur.execute(sql, data)
        count = cur.fetchone()[0]
        return 0, count
    except psy.DatabaseError, e:
        return 1, None


def get_number_tags_user(conn, uname):
    """
    Get the number of distinct tagnames used by the user.

    Note that you need to eliminate the duplication.

    :param conn: A postgres database connection object
    :param uname:  A string of username
    :return:
        (0, count)
            Success, retval is an integer indicating the number of tagnames used by the user
        (1, None)
            Failure
    """
    # kfuh
    try:
        cur = conn.cursor()
        sql = "SELECT COUNT(DISTINCT tagname) FROM tags t INNER JOIN papers p \
            on t.pid = p.pid WHERE p.username = %s;"
        data = (uname,)
        cur.execute(sql, data)
        count = cur.fetchone()[0]
        return 0, count
    except psy.DatabaseError, e:
        return 1, None
