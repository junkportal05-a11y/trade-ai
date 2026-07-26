import app.core.security as auth_helpers

print("Registry for apex_head_quant:")
print(auth_helpers.USER_REGISTRY.get('apex_head_quant'))

user_obj = auth_helpers.authenticate_user('apex_head_quant', 'password123')
print("\nAuthenticate 'password123' result:")
print(user_obj)

code_user, code_obj = auth_helpers.authenticate_by_code('password123')
print("\nAuthenticate by code result:")
print(f"User: {code_user}, Obj: {code_obj}")
