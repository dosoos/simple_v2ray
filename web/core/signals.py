from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.models import GlobalRevision, ProxyUser

_suppress_revision = False


@contextmanager
def suppress_proxy_revision():
    global _suppress_revision
    _suppress_revision = True
    try:
        yield
    finally:
        _suppress_revision = False


def _bump_revision():
    if _suppress_revision:
        return
    GlobalRevision.get_singleton()
    GlobalRevision.objects.filter(pk=1).update(revision=F("revision") + 1)


@receiver(post_save, sender=ProxyUser)
def proxy_user_saved(_sender, **_kwargs):
    _bump_revision()


@receiver(post_delete, sender=ProxyUser)
def proxy_user_deleted(_sender, **_kwargs):
    _bump_revision()


User = get_user_model()


@receiver(post_save, sender=User)
def auth_user_saved(sender, instance, **_kwargs):
    """
    固定 ProxyUser.label：优先 email，否则 username。
    当 Django 用户被修改时，同步刷新关联的代理管理记录。
    """
    try:
        proxy = instance.proxy_profile
    except Exception:
        return
    derived = ProxyUser.derive_label_from_user(instance)
    if derived and proxy.label != derived:
        proxy.label = derived
        proxy.save(update_fields=["label", "updated_at"])

