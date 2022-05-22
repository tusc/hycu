# HYCU REST Api example scripts
## Project Notes

**Author:** Carlos Talbot

The scripts in this folder are example scripts that can be used with HYCU's REST api. The scripts rely on a username and password which is used initially to request a bearer token for subsequent api calls. The username and password are hashed in base 64 and passed through an SSL connection.

The scripts with a suffix of by_apikey authenticate with a preconfigured API key from the UI. This allows you to store the API key in the script without relying on a username and passowrd. The API key can also be configured to expire after some time.
