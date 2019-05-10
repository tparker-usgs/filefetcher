#!/usr/bin/env python

from datetime import datetime, timedelta
import psutil
import os
import tomputils.util as tutil

MAX_RUN_TIME = timedelta(hours=24)


def main():
    logger = tutil.setup_logging("filefetcher - errors")
    tmp_dir = tutil.get_env_var('FF_TMP_DIR')
    for filename in os.listdir(tmp_dir):
        if filename.endswith('.lock'):
            with open(os.path.join(tmp_dir, filename)) as file:
                pid = int(file.read())
                try:
                    process = psutil.Process(pid)
                except psutil.NoSuchProcess:
                    continue

                create_time = process.create_time()
                create_time = datetime.fromtimestamp(create_time)

                process_age = datetime.now() - create_time
                if process_age > MAX_RUN_TIME:
                    logger.info("Killing process %s, has been running for %s",
                                pid, process_age)
                    process.terminate()
                    print("pid: {} age: {}".format(pid, process_age))


if __name__ == '__main__':
    main()
