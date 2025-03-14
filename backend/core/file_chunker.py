import os
import hashlib
import shutil
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, BinaryIO


class FileChunker:
    """
    A class to handle the splitting of files into chunks and the reassembly of chunks into complete files.
    Also provides functionality for chunk verification using SHA-256 hashing.
    """

    def __init__(self, chunk_size: int = 512 * 1024):  # Default chunk size: 512 KB
        """
        Initialize the FileChunker with a specified chunk size.
        
        Args:
            chunk_size: Size of each chunk in bytes (default: 512 KB)
        """
        self.chunk_size = chunk_size
        
    def split_file(self, file_path: str, output_dir: str, create_manifest: bool = True) -> Dict:
        """
        Split a file into chunks and save them to the output directory.
        
        Args:
            file_path: Path to the file to be split
            output_dir: Directory to save the chunks
            create_manifest: Whether to create a manifest file with metadata (default: True)
            
        Returns:
            A dictionary containing information about the chunks (filename, total_chunks, chunk_size, hashes)
        """
        file_path = Path(file_path)
        output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a subdirectory specifically for this file's chunks
        chunks_dir = output_dir / file_path.stem
        chunks_dir.mkdir(exist_ok=True)
        
        # Get file size
        file_size = file_path.stat().st_size
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        
        # Dictionary to store chunk information
        chunk_info = {
            "filename": file_path.name,
            "total_chunks": total_chunks,
            "chunk_size": self.chunk_size,
            "file_size": file_size,
            "hashes": {}
        }
        
        with open(file_path, 'rb') as f:
            chunk_index = 0
            
            while True:
                # Read a chunk from the file
                data = f.read(self.chunk_size)
                if not data:
                    break
                
                # Generate chunk filename
                chunk_filename = f"{file_path.stem}_{chunk_index:04d}"
                chunk_path = chunks_dir / chunk_filename
                
                # Calculate hash for the chunk
                chunk_hash = hashlib.sha256(data).hexdigest()
                chunk_info["hashes"][chunk_index] = chunk_hash
                
                # Write chunk to file
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(data)
                
                chunk_index += 1
        
        # Create a manifest file with all the metadata
        if create_manifest:
            manifest_path = chunks_dir / f"{file_path.stem}_manifest.json"
            with open(manifest_path, 'w') as manifest_file:
                json.dump(chunk_info, manifest_file, indent=2)
        
        return chunk_info
    
    def reassemble_file(self, chunks_dir: str, output_path: str, manifest_path: Optional[str] = None, 
                        verify_chunks: bool = True) -> bool:
        """
        Reassemble chunks into a complete file.
        
        Args:
            chunks_dir: Directory containing the chunks
            output_path: Path where the reassembled file will be saved
            manifest_path: Path to the manifest file (if None, will look in chunks_dir)
            verify_chunks: Whether to verify chunk integrity using hashes
            
        Returns:
            True if reassembly was successful, False otherwise
        """
        chunks_dir = Path(chunks_dir)
        output_path = Path(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Find manifest file if not provided
        if manifest_path is None:
            manifest_files = list(chunks_dir.glob("*_manifest.json"))
            if not manifest_files:
                raise FileNotFoundError(f"No manifest file found in {chunks_dir}")
            manifest_path = manifest_files[0]
        else:
            manifest_path = Path(manifest_path)
        
        # Load manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        total_chunks = manifest["total_chunks"]
        chunk_hashes = manifest["hashes"]
        
        with open(output_path, 'wb') as output_file:
            for i in range(total_chunks):
                # Determine chunk filename based on index
                chunk_filename = f"{Path(manifest['filename']).stem}_{i:04d}"
                chunk_path = chunks_dir / chunk_filename
                
                if not chunk_path.exists():
                    raise FileNotFoundError(f"Chunk {chunk_filename} not found in {chunks_dir}")
                
                # Read chunk
                with open(chunk_path, 'rb') as chunk_file:
                    data = chunk_file.read()
                
                # Verify chunk if requested
                if verify_chunks and str(i) in chunk_hashes:
                    chunk_hash = hashlib.sha256(data).hexdigest()
                    expected_hash = chunk_hashes[str(i)]
                    
                    if chunk_hash != expected_hash:
                        raise ValueError(f"Chunk {i} failed integrity verification")
                
                # Write chunk to output file
                output_file.write(data)
        
        return True
    
    def get_chunk(self, file_path: str, chunk_index: int) -> bytes:
        """
        Read a specific chunk from a file without creating intermediate chunk files.
        
        Args:
            file_path: Path to the file
            chunk_index: Index of the chunk to retrieve
            
        Returns:
            The chunk data as bytes
        """
        file_path = Path(file_path)
        
        with open(file_path, 'rb') as f:
            # Seek to the position of the chunk
            f.seek(chunk_index * self.chunk_size)
            # Read chunk
            return f.read(self.chunk_size)
    
    def write_chunk(self, output_path: str, chunk_data: bytes, chunk_index: int, 
                    file_size: Optional[int] = None) -> None:
        """
        Write a chunk directly to its position in a file.
        
        Args:
            output_path: Path to the output file
            chunk_data: The chunk data to write
            chunk_index: Index position where to write the chunk
            file_size: Known file size (to preallocate if needed)
        """
        output_path = Path(output_path)
        
        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate position
        position = chunk_index * self.chunk_size
        
        # Open file in read+ mode if it exists, otherwise create it
        file_mode = 'r+b' if output_path.exists() else 'wb'
        
        with open(output_path, file_mode) as f:
            # Preallocate file if we know the size and the file is new
            if file_size and file_mode == 'wb':
                f.truncate(file_size)
            
            # Seek to the position and write the chunk
            f.seek(position)
            f.write(chunk_data)
    
    def verify_chunk(self, chunk_data: bytes, expected_hash: str) -> bool:
        """
        Verify the integrity of a chunk by comparing its hash.
        
        Args:
            chunk_data: The chunk data as bytes
            expected_hash: The expected SHA-256 hash
            
        Returns:
            True if the chunk is valid, False otherwise
        """
        actual_hash = hashlib.sha256(chunk_data).hexdigest()
        return actual_hash == expected_hash
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        Get information about a file without actually chunking it.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        file_path = Path(file_path)
        
        file_size = file_path.stat().st_size
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        
        return {
            "filename": file_path.name,
            "file_size": file_size,
            "chunk_size": self.chunk_size,
            "total_chunks": total_chunks
        }
    
    def create_empty_file(self, file_path: str, file_size: int) -> None:
        """
        Create an empty file of specified size to prepare for receiving chunks.
        
        Args:
            file_path: Path to the file to create
            file_size: Size of the file in bytes
        """
        file_path = Path(file_path)
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create empty file of specified size
        with open(file_path, 'wb') as f:
            f.truncate(file_size)


# Example usage
if __name__ == "__main__":
    # Example: Break down a file into chunks
    chunker = FileChunker(chunk_size=1024 * 1024)  # 1MB chunks
    
    # Split a file
    file_path = "example_file.txt"
    chunks_dir = "chunks"
    chunk_info = chunker.split_file(file_path, chunks_dir)
    print(f"Split {chunk_info['filename']} into {chunk_info['total_chunks']} chunks")
    
    # Reassemble the file
    output_path = "reassembled_file.txt"
    success = chunker.reassemble_file(chunks_dir + "/" + Path(file_path).stem, output_path)
    
    if success:
        print(f"Successfully reassembled file to {output_path}")