# -*- coding: utf-8 -*-

import os

import click
from flask import Flask, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from myblog.blueprints.admin import admin_bp
from myblog.blueprints.auth import auth_bp
from myblog.blueprints.blog import blog_bp
from myblog.extensions import bootstrap, db, login_manager, csrf, moment
from myblog.models import Admin, Category, Post, Comment, Link, Thought, Topic
from myblog.settings import config

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask('myblog')
    app.config.from_object(config[config_name])

    register_logging(app)
    register_extensions(app)
    register_blueprints(app)
    register_shell_context(app)
    register_template_context(app)
    register_commands(app)
    register_errors(app)

    return app


def register_logging(app):
    pass


def register_extensions(app):
    bootstrap.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    moment.init_app(app)


def register_blueprints(app):
    app.register_blueprint(blog_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp, url_prefix='/auth')


def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db, Admin=Admin, Thought=Thought, Post=Post, Category=Category, Topic=Topic, Comment=Comment)


def register_template_context(app):
    @app.context_processor
    def make_template_context():
        admin = Admin.query.first()
        categories = Category.query.order_by(Category.id).all()
        topics = Topic.query.order_by(Topic.name).all()
        links = Link.query.order_by(Link.name).all()

        if current_user.is_authenticated:
            unread_comments = Comment.query.filter_by(reviewed=False).count()
        else:
            unread_comments = None

        return dict(
            admin=admin, categories=categories, topics=topics,
            links=links, unread_comments=unread_comments)


def register_commands(app):
    @app.cli.command()
    @click.option('--drop', is_flag=True, help='Create after drop.')
    def initdb(drop):
        """Initialize the database."""
        if drop:
            click.confirm('This operation will delete the database, do you want to continue', abort=True)
            db.drop_all()
            click.echo('Drop tables')

        db.create_all()
        click.echo('Initialized databases.')

    @app.cli.command()
    @click.option('--username', prompt=True, help='The username used to login.')
    @click.option('--password', prompt=True, hide_input=True,
                  confirmation_prompt=True, help='The password used to login.')
    def init(username, password):
        """Buliding Cleanblog, just for you."""

        click.echo('Initializing the database...')
        db.create_all()

        admin = Admin.query.first()
        if admin is not None:
            click.echo('The administrator already exists, updating...')
            admin.username = username
            admin.set_password(password)
        else:
            click.echo('Creating the temporary adminstrator account...')
            admin = Admin(
                username=username,
                blog_title='Cleanlog',
                name='Syntomic',
                about='Anything about you.'
            )
            admin.set_password(password)
            db.session.add(admin)

        topic = Topic.query.first()
        if topic is None:
            click.echo('Creating the default category...')
            topic = Topic(name='Default')
            db.session.add(topic)

        db.session.commit()
        click.echo('Done.')

    @app.cli.command()
    @click.option('--thought', default=20, help='Quantity of thoughts, default is 20.')
    @click.option('--topic', default=10, help='Quantity of categories, default is 10.')
    @click.option('--post', default=50, help='Quantity of posts, default is 50.')
    @click.option('--comment', default=500, help='Quantity of comments, default is 500.')
    def forge(thought, topic, post, comment):
        """Generate fake datas."""
        from myblog.fakes import fake_admin, fake_thoughts, fake_categories, fake_topics, fake_comments, fake_links, fake_posts

        db.drop_all()
        db.create_all()

        click.echo('Generating the administrator...')
        fake_admin()

        click.echo('Generating %d thoughts...' % thought)
        fake_thoughts(thought)

        click.echo('Generating 4 categories...')
        fake_categories()

        click.echo('Generating %d topics...' % topic)
        fake_topics(topic)

        click.echo('Generating %d posts...' % post)
        fake_posts(post)

        click.echo('Generating %d comments...' % comment)
        fake_comments(comment)

        click.echo('Generating links...')
        fake_links()

        click.echo('Done.')


def register_errors(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/400.html', description=e.description), 400
