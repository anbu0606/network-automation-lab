#!/usr/bin/env bash
# Give the four Lab 1 hosts their IP and default gateway (run after every deploy).
for h in "client1 20.238.131.20 20.238.131.1" "intranet 20.238.124.10 20.238.124.1" "web 20.238.155.11 20.238.155.1" "ssh 20.238.232.10 20.238.232.1"; do
  set -- $h
  docker exec clab-netsim-ospf-$1 sh -c "ip addr replace $2/24 dev eth1 && ip route replace default via $3" && echo "$1 ok"
done
