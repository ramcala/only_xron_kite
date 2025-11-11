#!/usr/bin/env python
"""Admin management CLI tool for Kite Order Scheduler."""

import click
from app import create_app
from models import db, Admin
from sqlalchemy.exc import IntegrityError


@click.group()
def cli():
    """Admin management commands."""
    pass


@cli.command()
@click.option('--username', prompt='Username', help='Admin username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--email', prompt='Email (optional)', default='', help='Admin email')
def create_admin(username, password, email):
    """Create a new admin user."""
    app = create_app()
    with app.app_context():
        # Check if admin already exists
        existing = Admin.query.filter_by(username=username).first()
        if existing:
            click.echo(f"Error: Admin '{username}' already exists.", err=True)
            return
        
        # Create new admin
        admin = Admin(username=username, email=email or None)
        admin.set_password(password)
        
        try:
            db.session.add(admin)
            db.session.commit()
            click.echo(f"✓ Admin '{username}' created successfully!")
        except IntegrityError as e:
            db.session.rollback()
            click.echo(f"Error: {str(e)}", err=True)
        except Exception as e:
            db.session.rollback()
            click.echo(f"Error: {str(e)}", err=True)


@cli.command()
def list_admins():
    """List all admin users."""
    app = create_app()
    with app.app_context():
        admins = Admin.query.all()
        if not admins:
            click.echo("No admins found.")
            return
        
        click.echo("\nAdmin Users:")
        click.echo("-" * 60)
        for admin in admins:
            click.echo(f"ID: {admin.id}")
            click.echo(f"  Username: {admin.username}")
            click.echo(f"  Email: {admin.email or 'N/A'}")
            click.echo(f"  Created: {admin.created_at}")
            click.echo()


@cli.command()
@click.option('--username', prompt='Username', help='Admin username to delete')
@click.confirmation_option(prompt='Are you sure you want to delete this admin?')
def delete_admin(username):
    """Delete an admin user."""
    app = create_app()
    with app.app_context():
        admin = Admin.query.filter_by(username=username).first()
        if not admin:
            click.echo(f"Error: Admin '{username}' not found.", err=True)
            return
        
        try:
            db.session.delete(admin)
            db.session.commit()
            click.echo(f"✓ Admin '{username}' deleted successfully!")
        except Exception as e:
            db.session.rollback()
            click.echo(f"Error: {str(e)}", err=True)


@cli.command()
@click.option('--username', prompt='Username', help='Admin username to update password')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='New password')
def change_password(username, password):
    """Change admin password."""
    app = create_app()
    with app.app_context():
        admin = Admin.query.filter_by(username=username).first()
        if not admin:
            click.echo(f"Error: Admin '{username}' not found.", err=True)
            return
        
        try:
            admin.set_password(password)
            db.session.commit()
            click.echo(f"✓ Password for '{username}' updated successfully!")
        except Exception as e:
            db.session.rollback()
            click.echo(f"Error: {str(e)}", err=True)


if __name__ == '__main__':
    cli()
