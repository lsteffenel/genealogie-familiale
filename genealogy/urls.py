from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.PersonListView.as_view(), name="person_list"),
    path("personnes/", views.PersonListView.as_view(), name="person_list"),
    path("arbre/", views.tree_view, name="tree"),
    path("arbre/<int:pk>/", views.tree_view, name="tree_root"),
    path("personne/<int:pk>/", views.PersonDetailView.as_view(), name="person_detail"),
    path(
        "personne/<int:pk>/proposer/",
        views.propose_person_edit,
        name="propose_person_edit",
    ),
    path("photos/ajouter/", views.propose_media_add, name="propose_media_add"),
    path("propositions/", views.proposal_list, name="proposal_list"),
    path("propositions/<int:pk>/", views.proposal_review, name="proposal_review"),
    path("connexion/", auth_views.LoginView.as_view(template_name="genealogy/login.html"), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
]
