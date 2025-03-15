# Prompt untuk Membuat Frontend CDR Analyzer dengan Cytoscape.js

Buatkan saya aplikasi frontend untuk CDR Analyzer yang terintegrasi dengan backend FastAPI yang sudah ada. Aplikasi ini akan memvisualisasikan data Call Detail Records (CDR) menggunakan Cytoscape.js dengan layout COSE.

## Spesifikasi Teknis:

1. **Framework**: React.js dengan TypeScript
2. **Visualisasi**: Cytoscape.js dengan layout COSE (https://github.com/cytoscape/cytoscape.js/tree/master/documentation/demos/cose-layout)
3. **Styling**: Tailwind CSS
4. **State Management**: React Context API atau Redux Toolkit
5. **API Integration**: Axios untuk komunikasi dengan backend
6. **Autentikasi**: Google Auth dengan Supabase dan penyimpanan token di localStorage

## Fitur yang Dibutuhkan:

### 1. Autentikasi dan Manajemen Pengguna
- Login dengan Google Auth melalui Supabase
- Halaman profil pengguna yang menampilkan informasi dari Google
- Logout functionality
- Semua pengguna baru otomatis disetujui (tidak perlu persetujuan manual)

### 2. Manajemen Session
- Halaman untuk membuat session baru dengan deskripsi
- Daftar session yang tersedia dengan opsi untuk memilih atau menghapus
- Detail session yang menampilkan jumlah record dan tanggal pembuatan

### 3. Upload File CDR
- Form untuk mengupload file CDR ke session yang dipilih
- Support untuk upload single file dan multiple files
- Progress bar dan notifikasi hasil upload

### 4. Visualisasi Graph
- Visualisasi interaktif data CDR menggunakan Cytoscape.js dengan layout COSE
- Node dengan tipe berbeda (phone, imei, location) harus memiliki bentuk dan warna yang berbeda
- Edge dengan ketebalan berbeda berdasarkan jumlah panggilan
- Tooltip yang menampilkan detail node/edge saat hover
- Panel informasi yang menampilkan detail node/edge saat diklik

### 5. Filter dan Analisis
- Filter berdasarkan tipe node (phone, imei, location)
- Filter berdasarkan rentang tanggal
- Filter berdasarkan durasi panggilan
- Pencarian node berdasarkan ID atau label
- Highlight path antara dua node yang dipilih

### 6. Ekspor dan Laporan
- Ekspor graph sebagai gambar (PNG/JPG)
- Ekspor data dalam format CSV atau JSON
- Laporan ringkasan yang menampilkan statistik graph

### 7. Nama Aplikasi
- Nama Aplikasi Reserse Ai
- Logo 

## Struktur API Backend:

### Endpoints Autentikasi:
- `POST /api/auth/google` - Autentikasi dengan Google
- `GET /api/auth/me` - Dapatkan informasi user saat ini

### Endpoints Session:
- `POST /api/sessions` - Buat session baru
- `GET /api/sessions` - Dapatkan daftar session
- `GET /api/sessions/{session_id}` - Dapatkan detail session
- `DELETE /api/sessions/{session_id}` - Hapus session

### Endpoints CDR:
- `POST /api/cdr/upload` - Upload file CDR tunggal
- `POST /api/cdr/upload-multiple` - Upload beberapa file CDR
- `POST /api/cdr/analyze` - Analisis data CDR dan dapatkan data graph

### Format Data Graph:
```json
{
  "nodes": [
    {
      "id": "6281234567890",
      "label": "6281234567890",
      "type": "phone"
    },
    {
      "id": "356912078685274",
      "label": "IMEI: 356912078685274",
      "type": "imei"
    }
  ],
  "edges": [
    {
      "source": "6281234567890",
      "target": "6287654321098",
      "weight": 5,
      "relationship": "calls",
      "calls": [
        {
          "date": "2018-04-12T21:46:45.0",
          "duration": 60,
          "call_type": "Voice MO"
        }
      ]
    }
  ]
}
```

## Perbaikan Autentikasi Backend untuk Google Auth

Untuk mengimplementasikan Google Auth dengan Supabase di backend, lakukan perubahan berikut:

1. Tambahkan konfigurasi Google Auth di Supabase:
   - Buka dashboard Supabase
   - Pergi ke Authentication > Providers
   - Aktifkan Google provider
   - Tambahkan Google Client ID dan Secret dari Google Cloud Console

2. Buat endpoint untuk autentikasi Google di `app/routers/auth.py`:

```python
@router.post("/auth/google", response_model=Token)
async def google_auth(
    token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk autentikasi dengan Google
    """
    try:
        # Verifikasi token Google dengan Supabase
        supabase_service = get_supabase_service()
        response = supabase_service.sign_in_with_google(token)
        
        # Sinkronisasi user ke database lokal
        user = supabase_service.sync_user_to_db(response.user, db)
        
        # Buat access token
        access_token = create_access_token(
            data={"sub": user.id}
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Error authenticating with Google: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi Google gagal",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

3. Tambahkan metode `sign_in_with_google` di `app/services/supabase_service.py`:

```python
def sign_in_with_google(self, token: str):
    """
    Sign in dengan Google token
    
    Args:
        token: Google ID token
        
    Returns:
        User data dari Supabase
    """
    try:
        response = self.client.auth.sign_in_with_idp({
            "provider": "google",
            "id_token": token
        })
        return response
    except Exception as e:
        logger.error(f"Error signing in with Google: {str(e)}")
        raise
```

4. Modifikasi fungsi `sync_user_to_db` untuk menangani data dari Google:

```python
def sync_user_to_db(self, user_data, db: Session) -> User:
    """
    Sinkronisasi data user dari Supabase ke database lokal
    
    Args:
        user_data: Data user dari Supabase
        db: Database session
        
    Returns:
        User object dari database
    """
    try:
        # Cek apakah user_data adalah objek atau dictionary
        if hasattr(user_data, 'id'):
            # Objek User dari Supabase
            user_id = user_data.id
            user_email = user_data.email
            user_metadata = getattr(user_data, 'user_metadata', {}) or {}
            
            # Ambil data dari Google jika ada
            if 'provider_id' in user_metadata and user_metadata['provider_id'] == 'google':
                username = user_metadata.get('full_name', '').replace(' ', '_').lower()
                full_name = user_metadata.get('full_name', '')
                avatar_url = user_metadata.get('avatar_url', '')
            else:
                username = user_metadata.get('username', '')
                full_name = user_metadata.get('full_name', '')
                avatar_url = None
        else:
            # Dictionary
            user_id = user_data["id"]
            user_email = user_data["email"]
            user_metadata = user_data.get("user_metadata", {}) or {}
            
            # Ambil data dari Google jika ada
            if 'provider_id' in user_metadata and user_metadata['provider_id'] == 'google':
                username = user_metadata.get('full_name', '').replace(' ', '_').lower()
                full_name = user_metadata.get('full_name', '')
                avatar_url = user_metadata.get('avatar_url', '')
            else:
                username = user_metadata.get("username", "")
                full_name = user_metadata.get("full_name", "")
                avatar_url = None
        
        # Cek apakah user sudah ada di database
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            # Buat user baru dan otomatis setujui
            user = User(
                id=user_id,
                email=user_email,
                username=username,
                full_name=full_name,
                avatar_url=avatar_url,
                is_active=True,
                is_approved=True  # Otomatis setujui user baru
            )
            db.add(user)
        else:
            # Update data user
            user.email = user_email
            user.username = username or user.username
            user.full_name = full_name or user.full_name
            if avatar_url:
                user.avatar_url = avatar_url
            user.is_active = True
            user.is_approved = True  # Pastikan user disetujui
        
        db.commit()
        db.refresh(user)
        
        return user
    except Exception as e:
        logger.error(f"Error syncing user to db: {str(e)}")
        raise
```

## Implementasi Google Auth di Frontend

Untuk mengimplementasikan Google Auth di frontend, gunakan Supabase Auth UI atau buat komponen kustom:

```tsx
import React, { useEffect } from 'react';
import { supabase } from '../../services/supabaseClient';
import { useAuth } from '../../hooks/useAuth';

const GoogleLogin: React.FC = () => {
  const { setUser, setLoading } = useAuth();

  const handleGoogleLogin = async () => {
    try {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: window.location.origin
        }
      });
      
      if (error) throw error;
    } catch (error) {
      console.error('Error logging in with Google:', error);
    }
  };

  useEffect(() => {
    // Check for auth state changes
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_IN' && session) {
          // Send the Google token to your backend
          try {
            const response = await fetch('/api/auth/google', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ token: session.provider_token }),
            });
            
            const data = await response.json();
            
            // Store the token from your backend
            localStorage.setItem('token', data.access_token);
            
            // Get user info
            const userResponse = await fetch('/api/auth/me', {
              headers: {
                Authorization: `Bearer ${data.access_token}`
              }
            });
            
            const userData = await userResponse.json();
            setUser(userData);
          } catch (error) {
            console.error('Error authenticating with backend:', error);
          } finally {
            setLoading(false);
          }
        }
      }
    );

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [setUser, setLoading]);

  return (
    <button
      onClick={handleGoogleLogin}
      className="flex items-center justify-center w-full px-4 py-2 space-x-2 text-white bg-blue-600 rounded hover:bg-blue-700 focus:outline-none"
    >
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12.545 10.239v3.821h5.445c-0.712 2.315-2.647 3.972-5.445 3.972-3.332 0-6.033-2.701-6.033-6.032s2.701-6.032 6.033-6.032c1.498 0 2.866 0.549 3.921 1.453l2.814-2.814c-1.798-1.677-4.198-2.707-6.735-2.707-5.523 0-10 4.477-10 10s4.477 10 10 10c8.396 0 10-7.326 10-10 0-0.665-0.057-1.302-0.168-1.917h-9.832z" />
      </svg>
      <span>Sign in with Google</span>
    </button>
  );
};

export default GoogleLogin;
```

## Struktur Folder yang Diharapkan:

```
src/
├── components/
│   ├── Layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Footer.tsx
│   ├── Auth/
│   │   ├── GoogleLogin.tsx
│   │   └── UserProfile.tsx
│   ├── Session/
│   │   ├── SessionList.tsx
│   │   ├── SessionCreate.tsx
│   │   └── SessionDetail.tsx
│   ├── CDR/
│   │   ├── FileUpload.tsx
│   │   └── UploadProgress.tsx
│   ├── Graph/
│   │   ├── CytoscapeGraph.tsx
│   │   ├── NodeDetail.tsx
│   │   ├── EdgeDetail.tsx
│   │   └── GraphControls.tsx
│   └── Filter/
│       ├── TypeFilter.tsx
│       ├── DateFilter.tsx
│       └── SearchFilter.tsx
├── services/
│   ├── api.ts
│   ├── supabaseClient.ts
│   ├── authService.ts
│   ├── sessionService.ts
│   └── cdrService.ts
├── hooks/
│   ├── useAuth.ts
│   ├── useSession.ts
│   └── useGraph.ts
├── context/
│   ├── AuthContext.tsx
│   ├── SessionContext.tsx
│   └── GraphContext.tsx
├── types/
│   ├── auth.ts
│   ├── session.ts
│   └── graph.ts
├── utils/
│   ├── cytoscapeConfig.ts
│   ├── graphUtils.ts
│   └── authUtils.ts
├── pages/
│   ├── LoginPage.tsx
│   ├── Dashboard.tsx
│   ├── SessionPage.tsx
│   └── GraphPage.tsx
├── routes/
│   ├── PrivateRoute.tsx
│   └── routes.ts
└── App.tsx
```

## Contoh Implementasi supabaseClient.ts:

```ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

## Contoh Implementasi useAuth.ts dengan Google Auth:

```tsx
import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { supabase } from '../services/supabaseClient';
import axios from 'axios';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  avatar_url?: string;
  is_approved: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return false;
    }

    try {
      const response = await axios.get('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      setUser(response.data);
      setLoading(false);
      return true;
    } catch (err) {
      localStorage.removeItem('token');
      setUser(null);
      setLoading(false);
      return false;
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const loginWithGoogle = async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: window.location.origin
        }
      });
      
      if (error) throw error;
    } catch (err: any) {
      setError(err.message || 'Error logging in with Google');
      throw err;
    }
  };

  const logout = async () => {
    try {
      await supabase.auth.signOut();
      localStorage.removeItem('token');
      setUser(null);
    } catch (err: any) {
      setError(err.message || 'Error logging out');
    }
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      error, 
      loginWithGoogle, 
      logout, 
      checkAuth,
      setUser,
      setLoading
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

## Contoh Implementasi LoginPage.tsx dengan Google Auth:

```tsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import GoogleLogin from '../components/Auth/GoogleLogin';
import { useAuth } from '../hooks/useAuth';

const LoginPage: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>;
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-8 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-gray-900">CDR Analyzer</h1>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to access your CDR analysis dashboard
          </p>
        </div>
        
        <div className="mt-8 space-y-6">
          <GoogleLogin />
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
```

## Contoh Implementasi CytoscapeGraph.tsx:

```tsx
import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import { useGraph } from '../../hooks/useGraph';
import { cytoscapeConfig } from '../../utils/cytoscapeConfig';

// Register the COSE layout
cytoscape.use(coseBilkent);

interface CytoscapeGraphProps {
  sessionId: string;
}

const CytoscapeGraph: React.FC<CytoscapeGraphProps> = ({ sessionId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const { graphData, loading, error, fetchGraphData } = useGraph();

  useEffect(() => {
    if (sessionId) {
      fetchGraphData(sessionId);
    }
  }, [sessionId, fetchGraphData]);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Initialize cytoscape
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: graphData.nodes.map(node => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.type
          }
        })),
        edges: graphData.edges.map(edge => ({
          data: {
            source: edge.source,
            target: edge.target,
            weight: edge.weight,
            relationship: edge.relationship,
            calls: edge.calls
          }
        }))
      },
      ...cytoscapeConfig
    });

    // Apply layout
    cyRef.current.layout({
      name: 'cose-bilkent',
      quality: 'default',
      nodeDimensionsIncludeLabels: true,
      fit: true,
      padding: 30,
      randomize: true,
      componentSpacing: 100,
      nodeRepulsion: 5000,
      idealEdgeLength: 100,
      edgeElasticity: 0.45,
      nestingFactor: 0.1,
      gravity: 0.25,
      numIter: 2500,
      tile: true,
      animate: 'end',
      animationDuration: 500,
      tilingPaddingVertical: 10,
      tilingPaddingHorizontal: 10,
      gravityRangeCompound: 1.5,
      gravityCompound: 1.0,
      gravityRange: 3.8
    }).run();

    // Event listeners
    cyRef.current.on('tap', 'node', function(evt) {
      const node = evt.target;
      console.log('Node clicked:', node.data());
      // Handle node selection
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [graphData]);

  if (loading) return <div>Loading graph data...</div>;
  if (error) return <div>Error loading graph: {error}</div>;
  if (!graphData) return <div>No graph data available</div>;

  return (
    <div className="w-full h-screen">
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
};

export default CytoscapeGraph;
```

Tolong implementasikan aplikasi frontend sesuai dengan spesifikasi di atas, dengan fokus khusus pada integrasi Cytoscape.js dengan layout COSE untuk visualisasi data CDR dan autentikasi Google melalui Supabase. Pastikan aplikasi memiliki UI yang intuitif dan responsif, serta dapat berkomunikasi dengan backend FastAPI yang sudah ada.
