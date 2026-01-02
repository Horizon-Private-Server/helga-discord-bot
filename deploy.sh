echo "Killing container ..."
docker container kill helga-discord-bot;

git stash;

echo "Pulling latest changes ...";
git pull origin main;
git stash pop;
echo "Rebuilding ..."        
docker build . --network=host -t helga-discord-bot;

echo "Starting ..."
docker run -d --rm -v $(pwd)/src/config.json:/code/src/config/config.json --network=host --name helga-discord-bot helga-discord-bot