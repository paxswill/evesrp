#!/bin/bash

if [[ -z $TRAVIS ]]; then
    exit 0
fi

if [[ $DB != "mysql"* ]]; then
    exit 0
fi

sudo service mysql stop

# Add MariaDB repository for Ubuntu 12.04 
sudo apt-get install python-software-properties
sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
sudo add-apt-repository 'deb http://nyc2.mirrors.digitalocean.com/mariadb/repo/10.0/ubuntu precise main'

sudo apt-get update
sudo apt-get -o Dpkg::Options::='--force-confold' install mariadb-server mariadb-client libmariadbclient-dev

sudo sed -i'' 's/table_cache/table_open_cache/' /etc/mysql/my.cnf
sudo sed -i'' 's/log_slow_queries/slow_query_log/' /etc/mysql/my.cnf
sudo sed -i'' 's/basedir[^=]\\+=.*$/basedir = \\/opt\\/mysql\\/server-5.6/' /etc/mysql/my.cnf

sudo service mysql restart
