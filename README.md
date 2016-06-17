# django-pgMemento
Django wrapper for pgMemento versioning approach for PostgreSQL using triggers and server-side functions in PL/pgSQL.

## Why PostgreSQL

The union of Django and PostgreSQL becomes more and more closer, if not implied. A few of the reasons: 
speed, customazibility, and reliability 

## Why [pgMemento](https://github.com/pgMemento/pgMemento)

Felix Kunde has done some extensive work and research to solution the optimal version control for PostgreSQL.
  I feel like writing my own pg triggers and functions to facilitate versioning would be like reinventing the wheel, 
  since pgMemento already is a great implementation of such. The future of pgMemento is to be provided as an extension,
  as well as solidified api, would simplify application implementation.
  
  
## What is logged
  
At the moment this package takes advantage of the DML logging part of pgMemento. However, pgMemento also provides ability
  to track DDL events as part of the logging procedure, that happens automatically. What does this mean in practice? It means
  that any schema changes are also reflected during logging, and can be reverted. Also, it means that after you make 
  changes to the database schema, your previous data logs are compatible with the new schema, and stay retrievable.

# Installation

1. Include the app in the settings:

    settings.py
    ```
    INSTALLED_APPS = [
        ...
        pg_memento
    ]
    
    PG_MEMENTO_IGNORE_TALBES = ['django_admin_log']  # optional
    ```

2. Initialize the logging by running the following management command:

    `python manage.py initlogging`
    
    The command will start logging on all tables in scema "public" (except those that are specified by PG_MEMENTO_IGNORE_TALBES)
    
    At this point all changes will be logged.

3. (Optional) Enable admin object log views:

    admin.py
    ```
    from pg_memento.admin import VersionModelAdmin
    
    admin.site.register(TestModel, VersionModelAdmin)  # register models
    ...
    ```
    
    Note: Admin model views are merely to be able to view the changes related to the object, it does not affect the
    logging in any way, since it's handles by Postgres and is completely independent of Django events.


That's it, start using the app, and see/revert the changes through "Row logs" admin view. Enjoy!