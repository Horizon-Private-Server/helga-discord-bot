docker build . --network=host -t helga-discord-bot;

echo "Starting ..."
docker run -it --rm --network=host --name helga-discord-bot helga-discord-bot