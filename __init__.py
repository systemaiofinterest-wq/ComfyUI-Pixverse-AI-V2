# __init__.py
from .PixVerse_Login_Gen_T2V_Unified_Node import PixVerseLoginGenT2VUnifiedNode
from .PixVerse_Login_Gen_I2V_Unified_Node import PixVerseLoginGenI2VUnifiedNode
from .PixVerse_Login_Gen_Extend_Unified_Node import PixVerseLoginGenExtendUnifiedNode


NODE_CLASS_MAPPINGS = {
    "PixVerseLoginGenT2VUnifiedNode": PixVerseLoginGenT2VUnifiedNode,
    "PixVerseLoginGenI2VUnifiedNode": PixVerseLoginGenI2VUnifiedNode,
    "PixVerseLoginGenExtendUnifiedNode": PixVerseLoginGenExtendUnifiedNode

}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PixVerseLoginGenT2VUnifiedNode": "🎬 PixVerse Login + Generate T2V Unified Node",
    "PixVerseLoginGenI2VUnifiedNode": "🎬 PixVerse Login + Generate I2V Unified Node",
    "PixVerseLoginGenExtendUnifiedNode": "🎬 PixVerse Login + Extend Unified Node",
 
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
