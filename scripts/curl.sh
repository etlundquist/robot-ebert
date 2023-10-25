
export ENDPOINT=http://127.0.0.1:8080
export ENDPOINT=https://robot-ebert-4diyefjzaq-uw.a.run.app

# user requests
# -------------

# create a new user
curl -X POST -H "Content-Type: application/json" -d '{"email": "etlundquist@gmail.com", "password": "cats", "fname": "eric", "lname": "lundquist"}' ${ENDPOINT}/users/

# add ratings for a user
curl -X POST -H "Content-Type: application/json" -d '[{"tmdb_id": "865", "rating": 1.0},{"tmdb_id": "866", "rating": 4.0}]' ${ENDPOINT}/users/85546704-ba75-47aa-b6e1-5800530466b6/ratings/

# get ratings for a user
curl -X GET -H "Content-Type: application/json" ${ENDPOINT}/users/85546704-ba75-47aa-b6e1-5800530466b6/ratings/

# get recommendations for a user
curl -X GET -H "Content-Type: application/json" "${ENDPOINT}/users/1/recommendations/?k=3"

# search requests
# ---------------

# get search recommendations for an anonymous user
curl -X POST -H "Content-Type: application/json" -d '{"query": "a gritty crime drama set in new york city starring al pacino", "k": 3}' ${ENDPOINT}/search/

# get search recommendations for an identifier user
curl -X POST -H "Content-Type: application/json" -d '{"query": "a gritty crime drama set in new york city starring al pacino", "user_id": "1", "k": 3}' ${ENDPOINT}/search/
