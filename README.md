# OAuth2 Callback Proxy

This is an example of how to use an OAuth2 Callback Proxy to reuse the same Google OAuth application across multiple development and preview environments. 

## Deploy the OAuth2 Callback Proxy

1. Create a namespace for your proxy
1. Create a Google OAuth2 Applicaton in your google cloud console, setting the value of `Authorized redirect URIs` to `https://auth-<namespace>.okteto.example.com/oauth2/callback` (replace <namespace> and `okteto.example.com` accordingly)
1. Download the clientId and clientSecret
1. Create the following Okteto admin secrets with the values (replace <namespace> and `okteto.example.com` accordingly):

        OAUTH2_CLIENT_ID=<your google oauth client id>
        OAUTH2_CLIENT_SECRET=<your google oauth client secret>
        OAUTH2_PROXY_URL=https://auth-<namespace>.okteto.example.com/oauth2/callback

1. Deploy your proxy into the namespace you created on step 1: 

        cd oauth
        okteto deploy -n=<namespace>

## Deploy the Sample Application

1. Create a second namespace for the sample application. This is the application that will use the callback proxy to authenticate. 
2. Deploy the application

        cd vote
        okteto deploy -n=<namespace>
3. Access the application using the https endpoint that Okteto created for you