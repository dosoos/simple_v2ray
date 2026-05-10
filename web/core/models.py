import uuid

from django.conf import settings
from django.db import models


class SyncCursor(models.Model):
    """从节点记录上次已同步的用户版本。"""

    last_user_revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "同步游标"
        verbose_name_plural = verbose_name

    @classmethod
    def get_singleton(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"last_user_revision": 0})
        return obj


class GlobalRevision(models.Model):
    """单调递增版本号，供从节点增量同步。"""

    revision = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "全局同步版本"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"rev-{self.revision}"

    @classmethod
    def get_singleton(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"revision": 1})
        return obj


class Node(models.Model):
    class Role(models.TextChoices):
        MASTER = "master", "主节点"
        SLAVE = "slave", "从节点"

    node_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="节点固定标识（展示与加入登记），易被仿冒，仅作名称/配对用",
    )
    name = models.CharField(max_length=128, help_text="节点显示名称")
    bearer_token = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        editable=False,
        help_text="同步 API 密钥，请求头 Authorization: Bearer …；撤销后须重新加入",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MASTER)
    enabled = models.BooleanField(default=True)
    base_url = models.URLField(blank=True, help_text="本面板对外访问地址，可选")
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    is_local = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "节点管理"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} ({self.role})"

    @classmethod
    def get_or_create_local(cls):
        """本机面板对应的单条 Node（is_local=True），用于采集与主从通信。"""
        from core import config

        node = cls.objects.filter(is_local=True).first()
        if node is not None:
            return node
        return cls.objects.create(
            name=config.NODE_NAME,
            role=config.NODE_ROLE,
            is_local=True,
            enabled=True,
        )


class ProxyUser(models.Model):
    """V2Ray 入站客户端（VMess），与 Django 用户一对一绑定。"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="proxy_profile",
        null=True,
        blank=True,
    )
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    label = models.CharField(
        max_length=128,
        help_text="对应 V2Ray 客户端 email 字段，用于统计匹配",
    )
    alter_id = models.PositiveSmallIntegerField(default=0)
    level = models.PositiveSmallIntegerField(default=0)
    enabled = models.BooleanField(default=True)
    traffic_limit_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="可选流量上限（字节），仅展示/扩展用，当前不强制断开",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "代理管理"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} ({self.uuid})"

    @staticmethod
    def derive_label_from_user(user) -> str:
        email = (getattr(user, "email", "") or "").strip()
        if email:
            return email
        username = (getattr(user, "username", "") or "").strip()
        return username or ""

    def save(self, *args, **kwargs):
        if self.user_id:
            derived = self.derive_label_from_user(self.user)
            if derived:
                self.label = derived
        super().save(*args, **kwargs)


class TrafficSnapshot(models.Model):
    """从 V2Ray Stats 拉取的累计计数快照，用于区间用量估算。"""

    user = models.ForeignKey(
        ProxyUser,
        on_delete=models.CASCADE,
        related_name="traffic_snapshots",
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traffic_snapshots",
    )
    recorded_at = models.DateTimeField(db_index=True)
    uplink_bytes = models.BigIntegerField()
    downlink_bytes = models.BigIntegerField()

    class Meta:
        verbose_name = "流量快照"
        verbose_name_plural = "流量快照"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["user", "recorded_at"]),
        ]

    def __str__(self):
        return f"{self.user.label} @ {self.recorded_at}"

