cd /
npm install --global yarn
rm -r bgutil-ytdlp-pot-provider
git clone --single-branch --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git
cd bgutil-ytdlp-pot-provider/server/
yarn install --frozen-lockfile
npx tsc
# node build/main.js