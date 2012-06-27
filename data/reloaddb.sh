#!/bin/bash
psql -c "drop schema public cascade;" armada
psql -c "create schema public" armada
psql -f $1 -1 armada
psql -c "\d" -t -q -o temp.txt armada
cat temp.txt |cut -d'|' -f2|sed "s/\ //g" > eve_table_names.txt
rm temp.txt
psql -f eve_typeattributes_view.sql armada
