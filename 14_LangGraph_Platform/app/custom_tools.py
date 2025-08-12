from app.rag import _get_rag_graph
from langchain_core.tools import tool

@tool
def tell_a_story_about_user(n: int):
    """Generate a made-up story about the user"""
    list_of_names = [
            'Katrina', 'Eric', 'Lily', 'Luna', 'Ray', 'Gianna', 'James', 'Tyler', 'Star', 'JJ',
            'Cefca', 'Gin 1', 'Tiger', 'Gin', 'Jace', 'Jose', 'RJ', 'DJ', 'Daniel', 'Emily',
            'Andrew', 'Kailie', 'Dana', 'Jessica', 'Rich', 'Dad', 'GJ', 'Gon', 'Gon', 'Emma',
            'Mair', 'Rune', 'Nova', 'Sol', 'Dune', 'Dinn', 'Ace', 'Acer', 'Iso', 'Iser',
            'Tide', 'Tile', 'Rise', 'Rye', 'Ryu', 'Lulu', 'Mom', 'Joanna', 'Justin', 'Paul',
            'Brian', 'Gina', 'Sarah', 'Megan', 'Jana', 'Cyndi', 'Beth', 'Danny', 'Del', 'Del'
        ]
    n %= len(list_of_names)
    name = list_of_names[n]
    graph = _get_rag_graph()
    result = graph.invoke({"question": f"Tell a happy made-upstory about {name}"})
    return result