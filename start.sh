docker run \
-d \
--restart=always \
--name v2ray \
-v `pwd`/v2ray:/etc/v2ray \
-v `pwd`/v2ray/log:/var/log/v2ray \
v2fly/v2fly-core v2ray -config=/etc/v2ray/config.json

docker run \
-d \
--restart=always \
--name caddy \
--link v2ray \
-v `pwd`/caddy/Caddyfile:/etc/caddy/Caddyfile \
-v `pwd`/caddy/data:/data \
-v `pwd`/caddy/config:/config \
-p 80:80 \
-p 443:443 \
caddy
