CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'
UUID=$(uuidgen | tr [:lower:] [:upper:])

jq '.inbounds[0].settings.clients += [{"id": "'$UUID'","level": 0,"alterId": 0,"email": "'$1'","createtime":"'$(date "+%Y-%m-%dT%H:%M:%S")'","updatetime":"'$(date "+%Y-%m-%dT%H:%M:%S")'"}]' $CONFIG_FILE > $CONFIG_FILE.bak

mv $CONFIG_FILE.bak $CONFIG_FILE

docker restart v2ray > /dev/null

echo $UUID | tr -d '\n'
