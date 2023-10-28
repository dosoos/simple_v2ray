CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'

jq '.inbounds[0].settings.clients['$1'].id' $CONFIG_FILE | sed 's/[", ]//g' | tr -d '\n'
