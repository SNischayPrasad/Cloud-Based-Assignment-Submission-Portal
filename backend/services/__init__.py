"""
Service layer: business rules and resource-level authorization.

Routes stay thin (parse request -> call service -> return schema);
everything that decides WHAT is allowed lives here so it can be unit
tested and reused (e.g. by a serverless function or background worker).
"""
