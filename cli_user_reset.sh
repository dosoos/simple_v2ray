CONFIG_FILE=$(dirname "${BASH_SOURCE[0]}")'/v2ray/config.json'

docker exec v2ray v2ctl api --server=127.0.0.1:8080 StatsService.QueryStats 'reset: true' > /dev/null

for key in $(jq '.inbounds[0].settings.clients | keys | .[]' $CONFIG_FILE);
do
	EMAIL=$(eval "jq '.inbounds[0].settings.clients["$key"]' $CONFIG_FILE | grep email" | awk -F':' '{print $2}' | sed 's/[\", ]//g');

	echo $key

	echo $EMAIL

    	echo $(eval "jq '.inbounds[0].settings.clients["$key"]' $CONFIG_FILE" | grep -E "id|level|alterId|updatetime" | sed 's/[", ]//g');

	echo 'upload: '$(eval "docker exec v2ray v2ctl api --server=127.0.0.1:8080 StatsService.GetStats 'name: \"user>>>$EMAIL>>>traffic>>>uplink\"' || echo 'value: 0' " | grep value | sed 's/value: //g' | numfmt --to=iec );
	
	echo 'download: '$(eval "docker exec v2ray v2ctl api --server=127.0.0.1:8080 StatsService.GetStats 'name: \"user>>>$EMAIL>>>traffic>>>downlink\"' || echo 'value: 0' " | grep value | sed 's/value: //g' | numfmt --to=iec );

	echo '';
done
