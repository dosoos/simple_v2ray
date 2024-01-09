CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'

jq 'del(.inbounds[0].settings.clients['$1'])' $CONFIG_FILE > $CONFIG_FILE.bak

mv $CONFIG_FILE.bak $CONFIG_FILE

for key in $(jq '.inbounds[0].settings.clients | keys | .[]' $CONFIG_FILE);
do
    echo $key $(eval "jq '.inbounds[0].settings.clients["$key"]' $CONFIG_FILE" | grep -E "id|level|alterId|email|updatetime" | sed 's/[", ]//g');
    echo '';
done
