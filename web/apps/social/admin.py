from django.contrib import admin

from .models import Comment, Follow, Like, Post, Report


@admin.action(description="Ẩn bài viết đã chọn")
def hide_posts(modeladmin, request, queryset):
    queryset.update(is_hidden=True)


@admin.action(description="Hiện lại bài viết đã chọn")
def unhide_posts(modeladmin, request, queryset):
    queryset.update(is_hidden=False)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "short_body", "created_at", "is_hidden", "report_count")
    list_filter = ("is_hidden", "created_at")
    search_fields = ("body", "author__username")
    raw_id_fields = ("author", "job")
    filter_horizontal = ("tags",)
    actions = [hide_posts, unhide_posts]

    @admin.display(description="Nội dung")
    def short_body(self, obj):
        return obj.body[:80]

    @admin.display(description="Số báo cáo")
    def report_count(self, obj):
        return obj.reports.count()


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "created_at", "is_hidden")
    list_filter = ("is_hidden",)
    search_fields = ("body", "author__username")
    raw_id_fields = ("post", "author")


@admin.action(description="Đánh dấu Đã xử lý và ẨN bài viết")
def resolve_and_hide(modeladmin, request, queryset):
    Post.objects.filter(pk__in=queryset.values("post")).update(is_hidden=True)
    queryset.update(status=Report.Status.REVIEWED)


@admin.action(description="Bỏ qua báo cáo (giữ bài)")
def dismiss(modeladmin, request, queryset):
    queryset.update(status=Report.Status.DISMISSED)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "reporter", "reason", "status", "created_at")
    list_filter = ("status", "reason")
    raw_id_fields = ("post", "reporter")
    actions = [resolve_and_hide, dismiss]


admin.site.register(Like)
admin.site.register(Follow)
