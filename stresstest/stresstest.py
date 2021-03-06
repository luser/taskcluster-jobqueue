#!/usr/bin/env python3.3

import argparse
import http.client
import json
import sys
import threading
import time

from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

def get_conn(url):
    o = urlparse(url)
    return http.client.HTTPConnection(o.hostname, o.port)

def submitter_thread(url, count, delay):
    conn = get_conn(url)
    job = {'version': '0.1.0'}
    headers = {"Content-Type": "application/json",
               "Content-Length": len(json.dumps(job))}
    for i in range(count):
        conn.request("POST", "/0.1.0/job/new", json.dumps(job), headers)
        resp = conn.getresponse()
        time.sleep(delay)

def worker_thread(url, duration):
    global done
    conn = get_conn(url)
    while not done:
        #TODO: worker id
        conn.request('POST', '/0.1.0/job/claim')
        resp = conn.getresponse()
        job_id = None
        if resp.status == 200:
            try:
                job = json.loads(resp.read().decode().strip())
                job_id = job.get('job_id', None)
            except ValueError:
                pass
        else:
            #TODO: API should error if no jobs
            pass
        if job_id:
            time.sleep(duration)
            #TODO: complete data
            conn.request('POST', '/0.1.0/job/{0}/complete'.format(job_id))
            resp = conn.getresponse()
        else:
            # Just wait a second to try again
            time.sleep(1)

def jobs_remaining(url):
    u = urlopen(urljoin(url, "/0.1.0/jobs"))
    if u.getcode() != 200:
        raise Exception("Error fetching /jobs")
    return len(json.loads(str(u.read(), 'utf-8')))

def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs='?', default="http://localhost:8314",
                        help="URL of job queue server")
    parser.add_argument("--num-jobs", type=int, default=10,
                        help="Number of jobs to submit")
    parser.add_argument("--job-submit-delay", type=int, default=1,
                        help="Delay (in seconds) between submitting jobs")
    parser.add_argument("--num-workers", type=int, default=1,
                        help="Number of worker threads to start")
    parser.add_argument("--worker-duration", type=int, default=5,
                        help="Duration of a worker's task")
    args = parser.parse_args(args)

    global done
    done = False
    submitter = threading.Thread(target=submitter_thread,
                                 args=(args.url, args.num_jobs,
                                       args.job_submit_delay))
    submitter.start()
    workers = []
    for i in range(args.num_workers):
        w = threading.Thread(target=worker_thread,
                             args=(args.url, args.worker_duration))
        w.start()
        workers.append(w)
    submitter.join()
    while jobs_remaining(args.url):
        time.sleep(args.worker_duration)
    done = True
    for w in workers:
        w.join()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

