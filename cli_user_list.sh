CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'

for key in $(jq '.inbounds[0].settings.clients | keys | .[]' $CONFIG_FILE);
do

	EMAIL=$(eval "jq '.inbounds[0].settings.clients["$key"]' $CONFIG_FILE | grep email" | awk -F':' '{print $2}' | sed 's/[\", ]//g');

	echo $key
	
	echo $EMAIL

    	echo $(eval "jq '.inbounds[0].settings.clients["$key"]' $CONFIG_FILE" | grep -E "id|level|alterId|updatetime" | sed 's/[", ]//g');

	echo 'upload: '$(eval "docker exec v2ray v2ray api stats -regexp $EMAIL'.+uplink' | grep -e 'Total' || echo 'Total: 0B' " | sed 's/Total: //g' );

	echo 'download: '$(eval "docker exec v2ray v2ray api stats -regexp $EMAIL'.+downlink' | grep -e 'Total' || echo 'Total: 0B' " | sed 's/Total: //g' );

	echo '';

done
