CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'

jq -r '.inbounds[0].settings.clients['$1'].id' $CONFIG_FILE | tr -d '\n'
