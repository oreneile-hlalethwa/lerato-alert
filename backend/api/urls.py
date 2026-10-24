from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.Health.as_view()),
    path('users/register/', views.Register.as_view()),
    path('users/login/', views.Login.as_view()),
    path('users/settings/', views.Settings.as_view()),
    path('contacts/', views.Contacts.as_view()),
    path('contacts/<int:pk>/', views.ContactDetail.as_view()),
    path('alerts/', views.Alerts.as_view()),
    path('reports/', views.Reports.as_view()),
    path('services/nearby/', views.ServicesNearby.as_view()),
    path('ai/referral/', views.AIReferral.as_view()),
    path('ai/friend/', views.AIFriend.as_view()),
    path('ai/lesson/', views.AILesson.as_view()),
    path('lessons/suggest/', views.LessonSuggest.as_view()),
    path('fund/apply/', views.FundApply.as_view()),
    path('fund/donate/', views.FundDonate.as_view()),
    path('fund/summary/', views.FundSummary.as_view()),
    path('hotspots/', views.Hotspots.as_view()),
    path('vault/', views.Vault.as_view()),
    path('vault/<int:pk>/', views.VaultItemDetail.as_view()),
]