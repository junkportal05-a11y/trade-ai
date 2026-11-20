from app.core.security import create_access_token, decode_access_token

def test_token_creation_and_decoding():
    payload = {"sub": "test_user"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "test_user"
    print("Test passed: JWT access token created and decoded successfully")
