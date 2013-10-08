"""Management utilities."""


from fabric.contrib.console import confirm
from fabric.api import abort, env, local, settings, task


# GLOBALS
env.run = 'heroku run python manage.py'
HEROKU_ADDONS = (
    'cloudamqp:lemur',
    'heroku-postgresql:dev',
    'scheduler:standard',
    'memcachier:dev',
    'newrelic:standard',
    'pgbackups:auto-month',
    'sentry:developer',
)
HEROKU_CONFIGS = (
    'BUILDPACK_URL=https://github.com/jbarone/heroku-buildpack-python-plus',
    'DJANGO_SETTINGS_MODULE={{ project_name }}.settings.prod',
    'SECRET_KEY="{{ secret_key }}"',
    'AWS_ACCESS_KEY_ID=xxx',
    'AWS_SECRET_ACCESS_KEY=xxx',
    'AWS_STORAGE_BUCKET_NAME={{ project_name }}',
)
# END GLOBALS


# HELPERS
def cont(cmd, message):
    """Given a command, ``cmd``, and a message, ``message``, allow a user to
    either continue or break execution if errors occur while executing ``cmd``.

    :param str cmd: The command to execute on the local system.
    :param str message: The message to display to the user on failure.

    .. note::
        ``message`` should be phrased in the form of a question, as if 
        ``cmd``'s execution fails, we'll ask the user to press 'y' or 'n' to 
        continue or cancel exeuction, respectively.

    Usage::

        cont('heroku run ...', 
             "Couldn't complete {cmd}. Continue anyway?".format(cmd=cmd)
    """
    with settings(warn_only=True):
        result = local(cmd, capture=True)

    if message and result.failed and not confirm(message):
        abort('Stopped execution per user request.')
# END HELPERS


# DATABASE MANAGEMENT
@task
def syncdb():
    """Run a syncdb."""
    local('{run} syncdb --noinput'.format(**env))


@task
def migrate(app=None):
    """Apply one (or more) migrations. If no app is specified, fabric will
    attempt to run a site-wide migration.

    :param str app: Django app name to migrate.
    """
    if app:
        local('{run} migrate {app} --noinput'.format(app=app, **env))
    else:
        local('{run} migrate --noinput'.format(**env))

@task
def south_init(app):
    local('python manage.py schemamigration {app} --initial'.format(app=app))

@task
def south_update(app):
    local('python manage.py schemamigration {app} --auto'.format(app=app))
# END DATABASE MANAGEMENT


# FILE MANAGEMENT
@task
def collectstatic():
    """Collect all static files, and copy them to S3 for production usage."""
    local('{run} collectstatic --noinput'.format(**env))


@task
def compress():
    """Compress css and javascript files"""
    local('{run} compress'.format(**env))
# END FILE MANAGEMENT


# PROJECT MANAGEMENT
@task
def initialize():
    """Initialize local project after startproject"""
    local('rm -rf docs README.md')
    local('echo /{{ project_name }}/static > .gitignore')
    local('git init')
    local('git add .')
    local("git commit -m 'First commit'")

@task
def startapp(app):
    """Start a new django app"""
    local('mkdir {{ project_name }}/apps/{app}'.format(app=app))
    local('python manage.py startapp {app} {{ project_name }}/apps/{app}'
            .format(app=app))
# END PROJECT MANAGEMENT


# HEROKU MANAGEMENT
@task
def update():
    """Update project deployment on Heroku"""
    cont('git push heroku master',
         "Couldn't push your application to Heroku, continue anyway?")

    syncdb()
    migrate()
    collectstatic()
    compress()

    cont('{run} newrelic-admin validate-config - stdout'.format(**env),
         "Couldn't initialize New Relic, continue anyway?")

@task
def bootstrap(app=None):
    """Bootstrap your new application with Heroku, preparing it for a 
    production deployment. This will:

        - Create a new Heroku application.
        - Install all ``HEROKU_ADDONS``.
        - Sync the database.
        - Apply all database migrations.
        - Collect static files.
        - Compress css and js files.
        - Initialize New Relic's monitoring add-on.
    """
    if not app:
        app = '{{ project_name}}'

    cont('heroku apps:create {app}'.format(app=app),
         "Couldn't create the Heroku app, continue anyway?")

    for addon in HEROKU_ADDONS:
        cont('heroku addons:add {addon}'.format(addon=addon),
             "Couldn't add {addon} to your Heroku app, continue anyway?"
             .format(addon=addon))

    for config in HEROKU_CONFIGS:
        cont('heroku config:add config'.format(config=config),
             "Couldn't add config to your Heroku app, continue anyway?"
             .format(config=config))

    cont('git push heroku master',
         "Couldn't push your application to Heroku, continue anyway?")

    syncdb()
    migrate()
    collectstatic()
    compress()

    cont('{run} newrelic-admin validate-config - stdout'.format(**env),
         "Couldn't initialize New Relic, continue anyway?")


@task
def destroy(app=None):
    """Destroy this Heroku application. Wipe it from existance.

    .. note::
        This really will completely destroy your application. Think twice.
    """
    if not app:
        app = '{{ project_name }}'

    local('heroku apps:destroy --app {app}'.format(app=app))

# END HEROKU MANAGEMENT
