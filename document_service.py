# document_service.py
"""
Document Metadata Service
High-level API for managing collaborative documents using Chord DHT
"""

import requests
import json
import uuid
from datetime import datetime
from shared_config import get_all_nodes


class DocumentService:
    def __init__(self, chord_nodes=None):
        """
        Initialize document service
        
        Args:
            chord_nodes: List of chord node addresses. If None, uses shared_config
        """
        if chord_nodes is None:
            chord_nodes = get_all_nodes()
        
        self.chord_nodes = chord_nodes
        
        if not self.chord_nodes:
            raise ValueError("No Chord nodes configured")
    
    def _get_entry_node(self):
        """Get a random Chord node as entry point"""
        import random
        return random.choice(self.chord_nodes)
    
    def create_document(self, owner, title, content_location):
        """
        Create a new document and store metadata
        
        Args:
            owner: Document owner username
            title: Document title
            content_location: Path to actual document content
        
        Returns:
            tuple: (doc_id, result)
        """
        doc_id = str(uuid.uuid4())
        metadata = {
            "doc_id": doc_id,
            "title": title,
            "owner": owner,
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "content_location": content_location,
            "permissions": {
                owner: "owner"
            },
            "version": 1,
            "tags": []
        }
        
        # Store in Chord ring
        node = self._get_entry_node()
        try:
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/store",
                json={"key": doc_id, "value": json.dumps(metadata)},
                timeout=5
            )
            return doc_id, resp.json()
        except Exception as e:
            return doc_id, {"error": str(e)}
    
    def get_document_metadata(self, doc_id):
        """
        Retrieve document metadata
        
        Args:
            doc_id: Document ID
        
        Returns:
            dict: Document metadata or None if not found
        """
        node = self._get_entry_node()
        try:
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/retrieve",
                json={"key": doc_id},
                timeout=5
            )
            
            data = resp.json()
            if data.get('value'):
                return json.loads(data['value'])
            return None
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return None
    
    def share_document(self, doc_id, owner, target_user, permission="read"):
        """
        Share document with another user
        
        Args:
            doc_id: Document ID
            owner: Current owner (must match document owner)
            target_user: User to share with
            permission: Permission level ("read" or "write")
        
        Returns:
            dict: Result of operation
        """
        metadata = self.get_document_metadata(doc_id)
        
        if not metadata:
            return {"error": "Document not found"}
        
        if metadata['owner'] != owner:
            return {"error": "Not authorized - you are not the owner"}
        
        metadata['permissions'][target_user] = permission
        metadata['modified_at'] = datetime.now().isoformat()
        
        node = self._get_entry_node()
        try:
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/store",
                json={"key": doc_id, "value": json.dumps(metadata)},
                timeout=5
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def update_document(self, doc_id, user, updates):
        """
        Update document metadata
        
        Args:
            doc_id: Document ID
            user: User making the update
            updates: Dict of fields to update
        
        Returns:
            dict: Result of operation
        """
        metadata = self.get_document_metadata(doc_id)
        
        if not metadata:
            return {"error": "Document not found"}
        
        if user not in metadata['permissions']:
            return {"error": "Not authorized"}
        
        # Apply updates (only allow certain fields)
        allowed_fields = ['title', 'tags', 'content_location']
        for key, value in updates.items():
            if key in allowed_fields:
                metadata[key] = value
        
        metadata['modified_at'] = datetime.now().isoformat()
        metadata['version'] += 1
        
        node = self._get_entry_node()
        try:
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/store",
                json={"key": doc_id, "value": json.dumps(metadata)},
                timeout=5
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def delete_document(self, doc_id, user):
        """
        Delete a document
        
        Args:
            doc_id: Document ID
            user: User requesting deletion
        
        Returns:
            dict: Result of operation
        """
        metadata = self.get_document_metadata(doc_id)
        
        if not metadata:
            return {"error": "Document not found"}
        
        if metadata['owner'] != user:
            return {"error": "Not authorized - only owner can delete"}
        
        node = self._get_entry_node()
        try:
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/delete",
                json={"key": doc_id},
                timeout=5
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    service = DocumentService()
    
    print("Document Service Example\n")
    
    # Create document
    print("1. Creating document...")
    doc_id, result = service.create_document(
        owner="alice",
        title="Project Proposal",
        content_location="/docs/proposal.pdf"
    )
    print(f"   Created: {doc_id}")
    print(f"   Result: {result}\n")
    
    # Retrieve metadata
    print("2. Retrieving metadata...")
    metadata = service.get_document_metadata(doc_id)
    if metadata:
        print(f"   Title: {metadata['title']}")
        print(f"   Owner: {metadata['owner']}")
        print(f"   Version: {metadata['version']}\n")
    
    # Share with another user
    print("3. Sharing with bob...")
    result = service.share_document(doc_id, "alice", "bob", "read")
    print(f"   Result: {result}\n")
    
    # Update document
    print("4. Updating tags...")
    result = service.update_document(doc_id, "alice", {"tags": ["important", "Q1-2024"]})
    print(f"   Result: {result}\n")
    
    # Verify update
    metadata = service.get_document_metadata(doc_id)
    if metadata:
        print(f"   Updated tags: {metadata['tags']}")
        print(f"   New version: {metadata['version']}")