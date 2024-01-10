CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'

for key in $(jq '.inbounds[0].settings.clients | keys | .[]' $CONFIG_FILE);
do

	EMAIL=$(eval "jq -r '.inbounds[0].settings.clients["$key"][\"email\"]' $CONFIG_FILE");

	echo $key
	
	echo $EMAIL

    	echo 'id: '$(eval "jq -r '.inbounds[0].settings.clients["$key"][\"id\"]' $CONFIG_FILE");

    	echo 'level: '$(eval "jq -r '.inbounds[0].settings.clients["$key"][\"level\"]' $CONFIG_FILE");

    	echo 'alterId: '$(eval "jq -r '.inbounds[0].settings.clients["$key"][\"alterId\"]' $CONFIG_FILE");

    	echo 'updatetime: '$(eval "jq -r '.inbounds[0].settings.clients["$key"][\"updatetime\"]' $CONFIG_FILE");

	echo 'upload: '$(eval "docker exec v2ray v2ray api stats -regexp $EMAIL'.+uplink' | grep -e 'Total' || echo 'Total: 0B' " | sed 's/Total: //g' );

	echo 'download: '$(eval "docker exec v2ray v2ray api stats -regexp $EMAIL'.+downlink' | grep -e 'Total' || echo 'Total: 0B' " | sed 's/Total: //g' );

	echo '';

done
