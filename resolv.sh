#!/bin/bash
CONTAINER=unboundec2_unbound-server_1
docker exec $CONTAINER host $@ localhost
