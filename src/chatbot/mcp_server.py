from chatbot.app import mcp

# Al importar db_tools, los decoradores @mcp.tool() se ejecutan y registran
import chatbot.tools.db_tools
import chatbot.tools.discord_tools
import chatbot.tools.rag_tools

if __name__ == "__main__":
    mcp.run()
