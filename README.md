# filefetcher



[![Code Climate](https://codeclimate.com/github/tparker-usgs/filefetcher/badges/gpa.svg)](https://codeclimate.com/github/tparker-usgs/filefetcher)



Retrieve files from remote dataloggers, while minimizing the impact on stressed telemetry links.



## Installation



filefetcher consists of a single python file. No installation is necessary beyond making sure that its dependancies are met. This can be done with `pip install -r requirements.txt`.



## Configuration



### Environment Variables



filefetcher looks to its environment for initial configuration. See example_configs/example.env for an example.



There is one required environment variable.

  * **FF_CONFIG_FILE** Path to configuration file.





filefetcher will, optionally, generate an email if error events are logged. To enable this behavior, three additional environment variables are required.

  * **MAILHOST** Hostname or IP address of mail forwarder.

  * **FF_SENDER** Address used for the From: header of generated email.

  * **FF_RECIPIENT** Address used for the To: header of generated email.



### Configuration File



The filefetcher configuration file is formatted in [YAML](http://yaml.org/). YAML is an expressive language and there are multiple ways to write a configuration file. Some examples are found in the example_configs/ directory. YAML can be fussy. There are several online validators which can help check configureation files if needed.



The filefetcher configuration conists of a list of queues which are processed concurrently. Each queue defines a list of dataloggers which are polled in sequqnce. This arangement allows filefetcher to retrive files quickly while accommodating networks which may be stressed and have limited available bandwidth. Each queue has a name and a list of data loggers. Optionally a boolean value may be set to indicate that the queue should not be processed, providing a way to pause polling of that queue without having to remove the configuration.



Each entry in the data logger list represents a single remote data logger. It has a name, an address, a pattern for formatting URLs for the remote files, and a location for retrieved files. Optionally a maximum transfer speed in bytes per second may be given. As with queues, polling of individual data loggers may also be paused. Data logger entries may also have a backfill directive, which will be explained below.



## Operation



### Standalone



filefetcher is run by executing the filefetcher.py script. At launch, filefetcher will read its environment variables, parse its config file and start polling. Polling will proceed one day at a time, polling each data logger for a given day before stepping back in time one day. Once filefetcher finds a daily file that has already been retrieved, or a daily file that cannot be retrieved from the remote data logger, polling for that logger will stop. Once polling for all data loggers in a queue has stopped, that polling process will exit. Once all polling processes have exited filefetcher will email any errors if configured to do so and will exit.



If a data logger entry has a backfill value, the process for exiting described above will be side stepped. Instead, polling will continue for all missing files day-by-day until the backfill date has been reached. 



### Docker



filefetcher runs well in a docker container. All files necessary to build an image are in the support/ directory. Most will need to be tweaked for your environment. Start with support/build.sh and go from there.  

