import base64
import io
from datetime import timedelta

import qrcode
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from core.models import GlobalRevision, Node, ProxyUser, SyncCursor, TrafficSnapshot
from core.utils import aggregate_traffic_for_user, build_vmess_share_link

admin.site.site_header = "个人 VPN 面板"
admin.site.site_title = "VPN 面板"
admin.site.index_title = "管理后台"


@admin.register(ProxyUser)
class ProxyUserAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "label",
        "uuid",
        "enabled",
        "alter_id",
        "created_at",
        "subscription_preview",
        "traffic_24h_display",
    )
    readonly_fields = (
        "uuid",
        "subscription_link",
        "subscription_qrcode",
        "traffic_24h_display",
        "traffic_7d_display",
        "traffic_30d_display",
        "traffic_365d_display",
    )
    search_fields = ("label", "uuid")
    list_filter = ("enabled",)
    autocomplete_fields = ("user",)

    @admin.display(description="订阅预览")
    def subscription_preview(self, obj):
        link = build_vmess_share_link(obj)
        return link if len(link) <= 48 else link[:45] + "..."

    @admin.display(description="订阅链接")
    def subscription_link(self, obj):
        return build_vmess_share_link(obj)

    @admin.display(description="订阅二维码")
    def subscription_qrcode(self, obj):
        link = build_vmess_share_link(obj)
        img = qrcode.make(link, box_size=4, border=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return format_html(
            '<img src="data:image/png;base64,{}" alt="qr" style="max-width:240px"/>',
            b64,
        )

    @admin.display(description="近24小时流量(字节)")
    def traffic_24h_display(self, obj):
        r = aggregate_traffic_for_user(
            obj, timezone.now() - timedelta(hours=24), timezone.now()
        )
        return f"↑{r['uplink_delta']} ↓{r['downlink_delta']} (样本{r['samples']})"

    @admin.display(description="近7天流量(字节)")
    def traffic_7d_display(self, obj):
        r = aggregate_traffic_for_user(
            obj, timezone.now() - timedelta(days=7), timezone.now()
        )
        return f"↑{r['uplink_delta']} ↓{r['downlink_delta']} (样本{r['samples']})"

    @admin.display(description="近30天流量(字节)")
    def traffic_30d_display(self, obj):
        r = aggregate_traffic_for_user(
            obj, timezone.now() - timedelta(days=30), timezone.now()
        )
        return f"↑{r['uplink_delta']} ↓{r['downlink_delta']} (样本{r['samples']})"

    @admin.display(description="近365天流量(字节)")
    def traffic_365d_display(self, obj):
        r = aggregate_traffic_for_user(
            obj, timezone.now() - timedelta(days=365), timezone.now()
        )
        return f"↑{r['uplink_delta']} ↓{r['downlink_delta']} (样本{r['samples']})"


@admin.register(TrafficSnapshot)
class TrafficSnapshotAdmin(admin.ModelAdmin):
    list_display = ("user", "node", "recorded_at", "uplink_bytes", "downlink_bytes")
    list_filter = ("node", "recorded_at")
    date_hierarchy = "recorded_at"
    search_fields = ("user__label",)


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "role",
        "enabled",
        "node_uuid",
        "bearer_status",
        "is_local",
        "last_heartbeat",
    )
    list_filter = ("role", "enabled", "is_local")
    search_fields = ("name",)
    readonly_fields = (
        "name",
        "role",
        "node_uuid",
        "bearer_token_display",
        "is_local",
        "base_url",
        "last_heartbeat",
        "created_at",
    )
    fields = (
        "enabled",
        "name",
        "role",
        "node_uuid",
        "bearer_token_display",
        "is_local",
        "base_url",
        "last_heartbeat",
        "created_at",
    )
    actions = ("revoke_bearer_tokens",)

    @admin.display(description="访问令牌", ordering="bearer_token")
    def bearer_status(self, obj):
        if not obj.bearer_token:
            return format_html('<span style="color:#888">已撤销</span>')
        t = obj.bearer_token
        if len(t) <= 12:
            return "已设置"
        return f"{t[:6]}…{t[-4:]}"

    @admin.display(description="Bearer 令牌（完整，请保密）")
    def bearer_token_display(self, obj):
        if not obj.bearer_token:
            return format_html(
                '<em style="color:#888">无令牌；请在从节点执行 join_master 重新领取</em>'
            )
        return format_html(
            '<code style="word-break:break-all">{}</code>',
            obj.bearer_token,
        )

    @admin.action(description="撤销访问令牌（从节点须重新执行 join_master）")
    def revoke_bearer_tokens(self, request, queryset):
        n = 0
        for obj in queryset:
            if obj.bearer_token:
                obj.bearer_token = None
                obj.save(update_fields=["bearer_token"])
                n += 1
        self.message_user(request, f"已撤销 {n} 个节点的 Bearer 令牌")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GlobalRevision)
class GlobalRevisionAdmin(admin.ModelAdmin):
    list_display = ("revision", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SyncCursor)
class SyncCursorAdmin(admin.ModelAdmin):
    list_display = ("last_user_revision", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
