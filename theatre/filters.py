import django_filters
from .models import Play, Genre, Actor, TheatreHall, Performance


class PlayFilter(django_filters.FilterSet):
    title = django_filters.ModelChoiceFilter(lookup_expr='icontains')
    genre = django_filters.ModelChoiceFilter(
        queryset=Genre.objects.all(),
        field_name='genre',
    )
    actors = django_filters.ModelMultipleChoiceFilter(
        queryset=Actor.objects.all(),
        field_name='actors',
    )

    class Meta:
        model = Play
        fields = {
            "title",
            "genre",
            "actors",
        }
