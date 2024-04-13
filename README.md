# Candore

## Introduction

`Candore` is the command line interface data integrity tool. The tool is build to verify the change made in a product has any impact on data in product.   

**The change** could be:
- Upgrade of the product to new version
- Some Patch applied to the product
- Developers made code changes locally / upstream etc
- Or any kind of change that we could  think of

**Verifications** that candore supports is:

- **Data loss** - The major impact that candore cares
- **Data Altered** - The change in data entity
- **Relation between the entities** -  Verifies if the link is not broken between entities


## Installation

```
$ mkdir ~/candore && cd ~/candore
$ pip install candore
```

## Configuration

The `candore` uses the `DynaConf` configuration python module to access the data in `settings.yaml`, it also allows an unique way of declaring secrets via Environment variables instead of putting in plain `settings.yaml`.

e.g: The password field can be set via environment variable by exporting the environment variable

```
# export CANDORE_CANDORE_PASSWORD = myPa$$worb"
```

### Configuration with PyPi package:

Copy/Download `settings.yaml.template` to local `~/candore` directory as `settings.yaml`, update it with the details and other configuration details for successful run.


## Usage Examples


* candore help:

```
# candore --help

Usage: candore [OPTIONS] COMMAND [ARGS]...

  A data integrity validation CLI tool for products post change

Options:
  --version                   Installed version of candore
  -s, --settings-file TEXT    Settings file path
  -c, --components-file TEXT  Components file path
  --help                      Show this message and exit.

Commands:
  apis     List API lister endpoints from Product
  compare  Compare pre and post upgrade data
  extract  Extract and save data using API lister endpoints
  reader   JSON Reader for reading the specific path data from entities...
```

There are 3 stages in which candore works:

1. Read data from the web server using APIs, before change:

```
# candore extract -o pre_entities.json --mode pre
```
This reads all data from web server before the change and saves in the json file in the current directory.


2. Read data from the web server using APIs, after change:

```
# candore extract -o post_entities.json --mode post
```
This reads all data from web server after the change and saves in the json file in the current directory.


3. Use the json data files to compare the data integrity:

```
# candore compare -t csv -o results.csv --pre pre_entities.json --post post_entities.json
```
This compares two json datasets and generates the reports of data integrity in CSV format in CSV file.

Reports could be generated in json:
```
# candore compare -t json -o results.json --pre pre_entities.json --post post_entities.json
```
