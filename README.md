# filefetcher

[![Code Climate](https://codeclimate.com/github/tparker-usgs/filefetcher/badges/gpa.svg)](https://codeclimate.com/github/tparker-usgs/filefetcher)

Retrieve files from remote dataloggers, while minimizing the impact on stressed telemetry links.

## Configuration

### Environment Variables

filefetcher looks to its environemnt for inital configuration. See example_configs/example.env for an example.

There is one required environment variable.
  * **FF_CONFIG_FILE** Path to configuration file.


filefetcher will, optionally, generate an email if error events are logged. To enable this behavior, three additional environemnt variables are required.
  * **MAILHOST** Hostname or IP address of mail forwarder.
  * **FF_SENDER** Address used for the From: header of generated email.
  * **FF_RECIPIENT** Address used for the To: header of generated email.

### Configuration File

The filefetcher configuration file is formatted in [YAML](http://yaml.org/) 1.2. YAML is an expressive language and there are multiple ways to write a configuration file. Some examples are found in the example_configs directory.

The filefetcher configuration conists of a list of queues, which are processed concurrently. Each queue defines a list of dataloggers which will be polled in sequqnce. This allows filefetcher to retrive files quickly while avoiding overwhelming the underlaying networks. Each queue has a name, a list of data loggers, and optionally a flag to indicate that the queue should not be processed.

Each entry in the data logger list represents a single remote data logger and has a name, an address, a pattern for formatting URLs for the remote files, a location for retrieved files, and optionally a maximum transfer speed in bytes per second.
