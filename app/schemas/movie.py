from pydantic import BaseModel, Field


class GenreResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class ActorResponse(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class DirectorResponse(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class MovieCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    release_year: int = Field(ge=1888, le=2100)
    price: float = Field(gt=0)
    imdb_rating: float | None = Field(default=None, ge=0, le=10)
    director_id: int | None = None
    genre_ids: list[int] = Field(default_factory=list)
    actor_ids: list[int] = Field(default_factory=list)


class MovieUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    release_year: int | None = Field(default=None, ge=1888, le=2100)
    price: float | None = Field(default=None, gt=0)
    imdb_rating: float | None = Field(default=None, ge=0, le=10)
    director_id: int | None = None
    genre_ids: list[int] | None = None
    actor_ids: list[int] | None = None


class MovieResponse(BaseModel):
    id: int
    title: str
    description: str
    release_year: int
    price: float
    imdb_rating: float | None
    director: DirectorResponse | None
    genres: list[GenreResponse]
    actors: list[ActorResponse]

    model_config = {"from_attributes": True}


class MovieListItemResponse(BaseModel):
    id: int
    title: str
    release_year: int
    price: float
    imdb_rating: float | None

    model_config = {"from_attributes": True}


class PaginatedMoviesResponse(BaseModel):
    items: list[MovieListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
