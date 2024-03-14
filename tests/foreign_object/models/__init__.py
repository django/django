from .article import Article, ArticleIdea, ArticleTag, ArticleTranslation, NewsArticle
from .customers import Address, Contact, Customer
from .empty_join import SlugPage
from .person import Country, Friendship, Group, Membership, Person
from .tenant import Tenant, TenantUser, TenantUserComment

__all__ = [
    "Address",
    "Article",
    "ArticleIdea",
    "ArticleTag",
    "ArticleTranslation",
    "Contact",
    "Country",
    "Customer",
    "Friendship",
    "Group",
    "Membership",
    "NewsArticle",
    "Person",
    "SlugPage",
    "Tenant",
    "TenantUser",
    "TenantUserComment",
]
