CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'

jq '.inbounds[0].settings.clients['$1'].updatetime = "'$(date "+%Y-%m-%dT%H:%M:%S")'"' $CONFIG_FILE > $CONFIG_FILE.bak

mv $CONFIG_FILE.bak $CONFIG_FILE

echo $1 $(jq '.inbounds[0].settings.clients['$1']' $CONFIG_FILE | grep -E "id|level|alterId|email|updatetime" | sed 's/[", ]//g')
