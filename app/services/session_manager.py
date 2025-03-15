import uuid
import os
import json
import networkx as nx
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DisconnectionError
from app.models.database_models import Session as DBSession, CDRRecord

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Mengelola session untuk analisis CDR.
    Setiap session menyimpan data CDR dan graph NetworkX.
    """
    
    def __init__(self):
        self.data_dir = "app/data"
        self._session_cache = {}  # Cache sederhana untuk menyimpan ID session yang valid
        
    def initialize(self):
        """Inisialisasi session manager dan buat direktori data jika belum ada"""
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info("Session manager initialized")
        
    def create_session(self, db: Session, name: str, description: Optional[str] = None) -> DBSession:
        """Buat session baru dan kembalikan session"""
        try:
            # Buat session baru di database
            session = DBSession(
                name=name,
                description=description,
                record_count=0,
                graph_data=json.dumps({"nodes": [], "edges": []})
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            # Tambahkan ke cache
            self._session_cache[session.id] = True
            
            logger.info(f"Created new session: {session.id}")
            return session
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    def get_session(self, db: Session, session_id: str) -> Optional[DBSession]:
        """Dapatkan session berdasarkan ID"""
        try:
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            if session:
                self._session_cache[session_id] = True
            return session
        except (OperationalError, DisconnectionError) as e:
            logger.error(f"Database connection error in get_session: {str(e)}")
            # Jika ada di cache, kembalikan True meskipun ada error koneksi
            return self._session_cache.get(session_id, False)
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None
    
    def get_all_sessions(self, db: Session) -> List[DBSession]:
        """Dapatkan semua session"""
        return db.query(DBSession).all()
    
    def session_exists(self, session_id: str, db: Optional[Session] = None) -> bool:
        """
        Cek apakah session ada berdasarkan ID
        
        Args:
            session_id: ID session yang akan dicek
            db: Session database (opsional). Jika tidak disediakan, akan menggunakan cache.
        
        Returns:
            bool: True jika session ada, False jika tidak
        """
        # Periksa dulu di cache
        if session_id in self._session_cache:
            return True
            
        # Jika db disediakan, periksa di database
        if db is not None:
            try:
                session = db.query(DBSession).filter(DBSession.id == session_id).first()
                exists = session is not None
                if exists:
                    # Tambahkan ke cache untuk penggunaan berikutnya
                    self._session_cache[session_id] = True
                return exists
            except (OperationalError, DisconnectionError) as e:
                logger.warning(f"Database connection error in session_exists: {str(e)}. Assuming session exists.")
                # Jika database error, asumsikan session ada untuk menghindari penolakan operasi
                return True
            except Exception as e:
                logger.error(f"Error checking if session exists: {str(e)}")
                return False
        
        # Jika session_id tidak di cache dan db tidak disediakan, asumsikan ada
        # Ini untuk backward compatibility dan menghindari error saat koneksi database bermasalah
        logger.warning(f"No DB provided to check session_id {session_id}, assuming it exists")
        return True
    
    def delete_session(self, db: Session, session_id: str) -> bool:
        """Hapus session berdasarkan ID"""
        try:
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            
            if not session:
                return False
            
            # Hapus semua CDR record terkait
            db.query(CDRRecord).filter(CDRRecord.session_id == session_id).delete()
            
            # Hapus session
            db.delete(session)
            db.commit()
            
            # Hapus dari cache jika ada
            if session_id in self._session_cache:
                del self._session_cache[session_id]
                
            logger.info(f"Deleted session: {session_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting session: {str(e)}")
            raise
    
    def add_cdr_data(self, db: Session, session_id: str, cdr_df: pd.DataFrame) -> int:
        """Tambahkan data CDR ke session dan perbarui graph"""
        try:
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            
            if not session:
                raise ValueError(f"Session {session_id} tidak ditemukan")
            
            # Tambahkan CDR records ke database
            for _, row in cdr_df.iterrows():
                # Helper function to safely get values from row
                def get_value(col: str) -> Optional[str]:
                    return row[col] if col in row and pd.notna(row[col]) else None
                
                cdr_record = CDRRecord(
                    call_type=row["call_type"],
                    anumber=row["anumber"],
                    bnumber=row["bnumber"],
                    cnumber=get_value("cnumber"),
                    date=row["date"],
                    duration=row["duration"],
                    lac_ci=get_value("lac_ci"),
                    imei=get_value("imei"),
                    imei_type=get_value("imei_type"),
                    imsi=get_value("imsi"),
                    sitename=get_value("sitename"),
                    direction=get_value("direction"),
                    latitude=get_value("latitude"),
                    longitude=get_value("longitude"),
                    session_id=session_id
                )
                db.add(cdr_record)
            
            # Commit perubahan
            db.commit()
            
            # Perbarui graph
            self._update_graph(db, session_id)
            
            # Perbarui jumlah record
            record_count = db.query(CDRRecord).filter(CDRRecord.session_id == session_id).count()
            session.record_count = record_count
            db.commit()
            
            logger.info(f"Added {len(cdr_df)} CDR records to session {session_id}")
            return len(cdr_df)
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding CDR data: {str(e)}")
            raise
    
    def _update_graph(self, db: Session, session_id: str):
        """Perbarui graph NetworkX berdasarkan data CDR"""
        try:
            # Dapatkan semua CDR records untuk session ini
            cdr_records = db.query(CDRRecord).filter(CDRRecord.session_id == session_id).all()
            
            # Buat graph baru
            G = nx.Graph()
            
            # Tambahkan node untuk setiap nomor telepon unik
            all_numbers = set()
            
            # Tambahkan A-numbers
            for record in cdr_records:
                if record.anumber != "000" and record.anumber != "UN":
                    all_numbers.add(record.anumber)
                    G.add_node(record.anumber, type="phone", label=record.anumber)
            
            # Tambahkan B-numbers
            for record in cdr_records:
                if record.bnumber != "000" and record.bnumber != "UN":
                    all_numbers.add(record.bnumber)
                    G.add_node(record.bnumber, type="phone", label=record.bnumber)
            
            # Tambahkan IMEI sebagai node dengan informasi perangkat
            imei_set = set()
            for record in cdr_records:
                if record.imei and record.imei != "UN":
                    imei_set.add(record.imei)
                    label = f"IMEI: {record.imei}"
                    if record.imei_type:
                        label += f"\n{record.imei_type}"
                    if record.imsi:
                        label += f"\nIMSI: {record.imsi}"
                    
                    G.add_node(record.imei,
                             type="imei",
                             label=label,
                             imei_type=record.imei_type,
                             imsi=record.imsi)
            
            # Tambahkan LAC_CI sebagai node
            lac_ci_set = set()
            for record in cdr_records:
                if record.lac_ci and record.lac_ci != "UN":
                    lac_ci_set.add(record.lac_ci)
                    G.add_node(record.lac_ci, type="location", label=f"LOC: {record.lac_ci}")
            
            # Tambahkan edge untuk setiap komunikasi
            for record in cdr_records:
                a_num = record.anumber
                b_num = record.bnumber
                
                # Tambahkan edge antara A dan B number jika keduanya valid
                if a_num in all_numbers and b_num in all_numbers:
                    # Cek apakah edge sudah ada
                    if G.has_edge(a_num, b_num):
                        # Tambahkan weight
                        G[a_num][b_num]["weight"] += 1
                        G[a_num][b_num]["calls"].append({
                            "date": record.date.isoformat(),
                            "duration": record.duration,
                            "call_type": record.call_type
                        })
                    else:
                        # Buat edge baru
                        G.add_edge(a_num, b_num, weight=1, calls=[{
                            "date": record.date.isoformat(),
                            "duration": record.duration,
                            "call_type": record.call_type
                        }])
                
                # Tambahkan edge antara nomor telepon dan IMEI
                if record.imei and record.imei != "UN" and a_num in all_numbers:
                    G.add_edge(a_num, record.imei, relationship="uses")
                
                # Tambahkan edge antara nomor telepon dan lokasi
                if record.lac_ci and record.lac_ci != "UN" and a_num in all_numbers:
                    location_id = record.lac_ci
                    location_label = f"LOC: {record.lac_ci}"
                    if record.sitename:
                        location_label += f" ({record.sitename})"
                    if record.latitude and record.longitude:
                        location_label += f"\n{record.latitude}, {record.longitude}"
                    
                    G.add_node(location_id,
                              type="location",
                              label=location_label,
                              sitename=record.sitename,
                              latitude=record.latitude,
                              longitude=record.longitude)
                    G.add_edge(a_num, location_id, relationship="located_at")
            
            # Simpan graph ke database
            session = db.query(DBSession).filter(DBSession.id == session_id).first()
            session.graph_data = json.dumps(self._graph_to_json(G))
            db.commit()
            
            logger.info(f"Updated graph for session {session_id}: {len(G.nodes)} nodes, {len(G.edges)} edges")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating graph: {str(e)}")
            raise
    
    def _graph_to_json(self, G: nx.Graph) -> Dict[str, List[Dict]]:
        """Konversi graph NetworkX ke format JSON"""
        nodes = []
        for node_id in G.nodes():
            node_data = G.nodes[node_id]
            node_type = node_data.get("type", "unknown")
            
            node = {
                "id": str(node_id),
                "label": node_data.get("label", str(node_id)),
                "type": node_type
            }
            
            nodes.append(node)
        
        edges = []
        for source, target, data in G.edges(data=True):
            edge = {
                "source": str(source),
                "target": str(target),
                "weight": data.get("weight", 1),
                "relationship": data.get("relationship", "calls"),
                "calls": data.get("calls", [])
            }
            
            edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def get_graph_data(self, db: Session, session_id: str, filter_options: Optional[dict] = None) -> Dict[str, List[Dict]]:
        """
        Dapatkan data graph dalam format yang sesuai untuk visualisasi di frontend
        """
        session = db.query(DBSession).filter(DBSession.id == session_id).first()
        
        if not session:
            raise ValueError(f"Session {session_id} tidak ditemukan")
        
        # Dapatkan data graph dari database
        graph_data = json.loads(session.graph_data)
        
        # Terapkan filter jika ada
        if filter_options:
            graph_data = self._apply_filters(graph_data, filter_options)
        
        return graph_data
    
    def _apply_filters(self, graph_data: Dict[str, List[Dict]], filter_options: dict) -> Dict[str, List[Dict]]:
        """
        Terapkan filter ke graph data
        """
        # Konversi ke graph NetworkX untuk memudahkan filtering
        G = nx.Graph()
        
        # Tambahkan nodes
        for node in graph_data["nodes"]:
            G.add_node(node["id"], **node)
        
        # Tambahkan edges
        for edge in graph_data["edges"]:
            G.add_edge(edge["source"], edge["target"], **edge)
        
        # Filter berdasarkan tipe node
        if "node_types" in filter_options:
            nodes_to_remove = []
            for node in G.nodes():
                node_type = G.nodes[node].get("type", "unknown")
                if node_type not in filter_options["node_types"]:
                    nodes_to_remove.append(node)
            
            G.remove_nodes_from(nodes_to_remove)
        
        # Filter berdasarkan tanggal
        if "date_range" in filter_options:
            start_date = filter_options["date_range"].get("start")
            end_date = filter_options["date_range"].get("end")
            
            if start_date or end_date:
                edges_to_remove = []
                
                for source, target, data in G.edges(data=True):
                    if "calls" in data:
                        valid_calls = []
                        
                        for call in data["calls"]:
                            call_date = call["date"]
                            
                            if start_date and call_date < start_date:
                                continue
                            
                            if end_date and call_date > end_date:
                                continue
                            
                            valid_calls.append(call)
                        
                        if not valid_calls:
                            edges_to_remove.append((source, target))
                        else:
                            data["calls"] = valid_calls
                            data["weight"] = len(valid_calls)
                
                G.remove_edges_from(edges_to_remove)
        
        # Hapus node yang terisolasi
        isolated_nodes = list(nx.isolates(G))
        G.remove_nodes_from(isolated_nodes)
        
        # Konversi kembali ke format JSON
        return self._graph_to_json(G)

# Singleton instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Dapatkan instance SessionManager (singleton)"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager 