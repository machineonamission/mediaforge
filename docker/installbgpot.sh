cd /
rm -r bgutil-ytdlp-pot-provider
git clone --single-branch --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git
cd bgutil-ytdlp-pot-provider/server/
# https://github.com/denoland/deno/issues/31181
sed -i 's|"github:tj/commander\.js\.git#develop"|"\^14.0.2"|g' package.json
deno install --allow-scripts=npm:canvas
#node build/main.js