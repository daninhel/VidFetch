const { generate } = require('youtube-po-token-generator');

generate().then(tokens => {
    console.log("Tokens generated: ", tokens);
}).catch(err => {
    console.error("Token err: ", err);
});
