fetch('/api/config')
                        .then(res => res.json())
                        .then(data => setDefaultConfig(data))
                        .catch(err => console.error('Kļūda ielādējot konfigurāciju:', err));
                        
                    // Ielādē sistēmas statusu
                    fetch('/api/status')
                        .then(res => res.json())
                        .then(data => {
                            setSystemStatus(data);
                            // Iestatām datumu diapazonu atbilstoši pieejamajiem failiem
                            if (data.status === 'ok' && data.files_by_date) {
                                const dates = Object.keys(data.files_by_date).sort();
                                if (dates.length > 0) {
                                    // Iestatām pēdējās 7 dienas vai visas pieejamās
                                    const endDate = new Date();
                                    const startDate = new Date();
                                    startDate.setDate(startDate.getDate() - 7);
                                    
                                    // Pārbaudām vai ir pietiekami dati
                                    const oldestAvailable = new Date(dates[0]);
                                    if (startDate < oldestAvailable) {
                                        setStartDate(dates[0]);
                                    } else {
                                        setStartDate(startDate.toISOString().split('T')[0]);
                                    }
                                    setEndDate(endDate.toISOString().split('T')[0]);
                                }
                            }
                        })
                        .catch(err => console.error('Kļūda ielādējot statusu:', err));
                }, []);
                
                const handleAddKeyword = (keyword) => {
                    if (keyword && !keywords.includes(keyword)) {
                        setKeywords([...keywords, keyword]);
                        setNewKeyword('');
                    }
                };
                
                const handleAddCpvCode = (code) => {
                    if (code && !cpvCodes.includes(code)) {
                        setCpvCodes([...cpvCodes, code]);
                        setNewCpvCode('');
                    }
                };
                
                const handleAddExcludeKeyword = (keyword) => {
                    if (keyword && !excludeKeywords.includes(keyword)) {
                        setExcludeKeywords([...excludeKeywords, keyword]);
                        setNewExcludeKeyword('');
                    }
                };
                
                const handleSearch = async () => {
                    setIsSearching(true);
                    setError(null);
                    setSearchResults(null);
                    setExpandedResults({});
                    
                    const searchData = {
                        start_date: startDate,
                        end_date: endDate,
                        keywords: keywords,
                        cpv_codes: cpvCodes,
                        exclude_keywords: excludeKeywords,
                        statuses: selectedStatuses,
                        deadline_status: deadlineStatus,
                        procedure_types: selectedProcedureTypes
                    };
                    
                    try {
                        const response = await fetch('/api/search', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(searchData)
                        });
                        
                        const data = await response.json();
                        
                        if (response.ok) {
                            setSearchResults(data);
                        } else {
                            setError(data.error || 'Meklēšanas kļūda');
                        }
                    } catch (err) {
                        setError('Nevar savienoties ar serveri: ' + err.message);
                    } finally {
                        setIsSearching(false);
                    }
                };
                
                const downloadResults = (format) => {
                    if (!searchResults || searchResults.totalFound === 0) return;
                    
                    if (format === 'json') {
                        const blob = new Blob([JSON.stringify(searchResults.results, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `iepirkumi_${new Date().toISOString().split('T')[0]}.json`;
                        a.click();
                    } else if (format === 'csv') {
                        // CSV eksports
                        let csv = 'Datums,Nosaukums,Pasūtītājs,CPV kodi,Vērtība,Termiņš,Statuss,Procedūras veids,Atslēgvārdi\\n';
                        searchResults.results.forEach(r => {
                            csv += `"${r.date}","${r.title}","${r.authority}","${r.cpvCodes.join(';')}","${r.value}","${r.deadline}","${r.status}","${r.procedureType}","${r.matchedKeywords.join(';')}"\\n`;
                        });
                        
                        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `iepirkumi_${new Date().toISOString().split('T')[0]}.csv`;
                        a.click();
                    }
                };
                
                const formatValue = (value) => {
                    if (!value || value === 'Nav norādīta') return value;
                    
                    // Mēģina formatēt kā skaitli ar valūtu
                    const match = value.match(/(\\d[\\d\\s.,]*\\d)\\s*(EUR|€)?/);
                    if (match) {
                        const num = match[1].replace(/\\s/g, '').replace(',', '.');
                        const currency = match[2] || 'EUR';
                        return `${parseFloat(num).toLocaleString('lv-LV')} ${currency}`;
                    }
                    return value;
                };
                
                const isDeadlineExpired = (deadline) => {
                    if (!deadline || deadline === 'Nav norādīts') return false;
                    try {
                        const deadlineDate = new Date(deadline);
                        return deadlineDate < new Date();
                    } catch {
                        return false;
                    }
                };
                
                const toggleProcedureGroup = (group, types) => {
                    const allSelected = types.every(type => selectedProcedureTypes.includes(type));
                    if (allSelected) {
                        // Noņem visus grupas tipus
                        setSelectedProcedureTypes(selectedProcedureTypes.filter(t => !types.includes(t)));
                    } else {
                        // Pievieno visus grupas tipus
                        const newTypes = [...selectedProcedureTypes];
                        types.forEach(type => {
                            if (!newTypes.includes(type)) {
                                newTypes.push(type);
                            }
                        });
                        setSelectedProcedureTypes(newTypes);
                    }
                };
                
                return (
                    <div className="min-h-screen bg-gray-50 py-8">
                        <div className="max-w-7xl mx-auto px-4">
                            {/* Header */}
                            <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
                                <h1 className="text-3xl font-bold text-gray-800 mb-2">
                                    Iepirkumu meklētājs
                                </h1>
                                <p className="text-gray-600">Meklējiet publiskos iepirkumus pēc atslēgvārdiem un CPV kodiem</p>
                            
                                {/* Sistēmas statuss */}
                                {systemStatus && (
                                    <div className="mt-4 text-sm">
                                        {systemStatus.status === 'ok' ? (
                                            <div className="bg-green-100 text-green-800 px-3 py-2 rounded">
                                                {systemStatus.message} | Pēdējā atjaunošana: {new Date(systemStatus.last_update).toLocaleString('lv-LV')}
                                            </div>
                                        ) : (
                                            <div className="bg-yellow-100 text-yellow-800 px-3 py-2 rounded">
                                                {systemStatus.message}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                            
                            {/* Error message */}
                            {error && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
                                    <strong>Kļūda:</strong> {error}
                                </div>
                            )}
                            
                            {/* Date selection */}
                            <div className="bg-white rounded-lg shadow p-6 mb-6">
                                <h2 className="text-xl font-semibold mb-4">Datumu diapazons</h2>
                                <div className="grid md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">No datuma</label>
                                        <input
                                            type="date"
                                            value={startDate}
                                            onChange={(e) => setStartDate(e.target.value)}
                                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Līdz datumam</label>
                                        <input
                                            type="date"
                                            value={endDate}
                                            onChange={(e) => setEndDate(e.target.value)}
                                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                </div>
                            </div>
                            
                            {/* Aktualitātes filtrs */}
                            <div className="bg-white rounded-lg shadow p-6 mb-6">
                                <h2 className="text-xl font-semibold mb-4">Iepirkuma aktualitāte</h2>
                                <div className="flex gap-4">
                                    <label className="flex items-center">
                                        <input
                                            type="radio"
                                            value="all"
                                            checked={deadlineStatus === 'all'}
                                            onChange={(e) => setDeadlineStatus(e.target.value)}
                                            className="mr-2"
                                        />
                                        <span>Visi</span>
                                    </label>
                                    <label className="flex items-center">
                                        <input
                                            type="radio"
                                            value="active"
                                            checked={deadlineStatus === 'active'}
                                            onChange={(e) => setDeadlineStatus(e.target.value)}
                                            className="mr-2"
                                        />
                                        <span className="text-green-600">Aktuāli</span>
                                    </label>
                                    <label className="flex items-center">
                                        <input
                                            type="radio"
                                            value="expired"
                                            checked={deadlineStatus === 'expired'}
                                            onChange={(e) => setDeadlineStatus(e.target.value)}
                                            className="mr-2"
                                        />
                                        <span className="text-red-600">Beigušies</span>
                                    </label>
                                </div>
                            </div>
                            
                            {/* Keywords */}
                            <div className="bg-white rounded-lg shadow p-6 mb-6">
                                <h2 className="text-xl font-semibold mb-4">Meklēšanas atslēgvārdi (neobligāti)</h2>
                                <p className="text-sm text-gray-600 mb-4">Atstājiet tukšu, lai redzētu visus iepirkumus</p>
                                <div className="space-y-4">
                                    <div className="flex flex-wrap gap-2">
                                        {keywords.map((keyword, index) => (
                                            <span key={index} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full flex items-center gap-2">
                                                {keyword}
                                                <button
                                                    onClick={() => setKeywords(keywords.filter((_, i) => i !== index))}
                                                    className="text-blue-600 hover:text-blue-800"
                                                >
                                                    ✕
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={newKeyword}
                                            onChange={(e) => setNewKeyword(e.target.value)}
                                            onKeyPress={(e) => e.key === 'Enter' && handleAddKeyword(newKeyword)}
                                            placeholder="Pievienot atslēgvārdu..."
                                            className="flex-1 p-2 border border-gray-300 rounded-lg"
                                        />
                                        <button
                                            onClick={() => handleAddKeyword(newKeyword)}
                                            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                                        >
                                            Pievienot
                                        </button>
                                    </div>
                                    {defaultConfig?.suggested_keywords && (
                                        <div className="text-sm text-gray-600">
                                            <span className="font-medium">Ieteikumi:</span>
                                            <div className="flex flex-wrap gap-2 mt-2">
                                                {defaultConfig.suggested_keywords.map((keyword) => (
                                                    <button
                                                        key={keyword}
                                                        onClick={() => handleAddKeyword(keyword)}
                                                        className="text-blue-600 hover:text-blue-800 underline"
                                                    >
                                                        {keyword}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                            
                            {/* CPV codes */}
                            <div className="bg-white rounded-lg shadow p-6 mb-6">
                                <h2 className="text-xl font-semibold mb-4">CPV kodi (neobligāti)</h2>
                                <div className="space-y-4">
                                    <div className="flex flex-wrap gap-2">
                                        {cpvCodes.map((code, index) => (
                                            <span key={index} className="bg-green-100 text-green-800 px-3 py-1 rounded-full flex items-center gap-2">
                                                {code}
                                                <button
                                                    onClick={() => setCpvCodes(cpvCodes.filter((_, i) => i !== index))}
                                                    className="text-green-600 hover:text-green-800"
                                                >
                                                    ✕
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={newCpvCode}
                                            onChange={(e) => setNewCpvCode(e.target.value)}
                                            onKeyPress={(e) => e.key === 'Enter' && handleAddCpvCode(newCpvCode)}
                                            placeholder="Pievienot CPV kodu..."
                                            className="flex-1 p-2 border border-gray-300 rounded-lg"
                                        />
                                        <button
                                            onClick={() => handleAddCpvCode(newCpvCode)}
                                            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                                        >
                                            Pievienot
                                        </button>
                                    </div>
                                    {defaultConfig?.common_cpv_codes && (
                                        <div className="grid md:grid-cols-2 gap-2 text-sm">
                                            {defaultConfig.common_cpv_codes.map((cpv) => (
                                                <button
                                                    key={cpv.code}
                                                    onClick={() => handleAddCpvCode(cpv.code)}
                                                    className="text-left p-2 hover:bg-gray-50 rounded"
                                                >
                                                    <span className="font-medium">{cpv.code}</span> - {cpv.name}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                            
                            {/* Excluded keywords */}
                            <div className="bg-white rounded-lg shadow p-6 mb-6">
                                <h2 className="text-xl font-semibold mb-4">Izslēgtie vārdi</h2>
                                <div className="space-y-4">
                                    <div className="flex flex-wrap gap-2">
                                        {excludeKeywords.map((keyword, index) => (
                                            <span key={index} className="bg-red-100 text-red-800 px-3 py-1 rounded-full flex items-center gap-2">
                                                {keyword}
                                                <button
                                                    onClick={() => setExcludeKeywords(excludeKeywords.filter((_, i) => i !== index))}
                                                    className="text-red-600 hover:text-red-800"
                                                >
                                                    ✕
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={newExcludeKeyword}
                                            onChange={(e) => setNewExcludeKeyword(e.target.value)}
                                            onKeyPress={(e) => e.key === 'Enter' && handleAddExcludeKeyword(newExcludeKeyword)}
                                            placeholder="Pievienot izslēgto vārdu..."
                                            className="flex-1 p-2 border border-gray-300 rounded-lg"
                                        />
                                        <button
                                            onClick={() => handleAddExcludeKeyword(newExcludeKeyword)}
                                            className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
                                        >
                                            Pievienot
                                        </button>
                                    </div>
                                </div>
                            </div>
                            
                            {/* Statusa filtri */}
                            <div className="bg-white rounded-lg shadow p-6 mb-6">
                                <h2 className="text-xl font-semibold mb-4">Iepirkuma statuss</h2>
                                <div className="space-y-2">
                                    {[
                                        { value: 'IZSLUDINĀTS', label: 'Izsludināts', color: 'blue' },
                                        { value: 'PIEDĀVĀJUMI ATVĒRTI', label: 'Piedāvājumi atvērti', color: 'yellow' },
                                        { value: 'LĪGUMS NOSLĒGTS', label: 'Līgums noslēgts', color: 'green' },
                                        { value: 'IZBEIGTS-PĀRTRAUKTS', label: 'Izbeigts/Pārtraukts', color: 'red' }
                                    ].map((status) => (
                                        <label key={status.value} className="flex items-center space-x-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={selectedStatuses.includes(status.value)}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setSelectedStatuses([...selectedStatuses, status.value]);
                                                    } else {
                                                        setSelectedStatuses(selectedStatuses.filter(s => s !== status.value));
                                                    }
                                                }}
                                                className="form-checkbox h-4 w-4 text-blue-600"
                                            />
                                            <span className={`text-sm bg-${status.color}-100 text-${status.color}-800 px-2 py-1 rounded`}>
                                                {status.label}
                                            </span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Procedūras tipu filtri */}
                            <div className="bg-white rounded-lg shadow p-6 mb-6">
                                <h2 className="text-xl font-semibold mb-4">Procedūras veids</h2>
                                <div className="space-y-4">
                                    {Object.entries(procedureGroups).map(([group, types]) => (
                                        <div key={group}>
                                            <div className="flex items-center mb-2">
                                                <button
                                                    onClick={() => toggleProcedureGroup(group, types)}
                                                    className="text-sm font-semibold text-gray-700 hover:text-blue-600"
                                                >
                                                    {types.every(t => selectedProcedureTypes.includes(t)) ? '☑' : '☐'} {group}
                                                </button>
                                            </div>
                                            <div className="ml-4 space-y-1">
                                                {types.map(type => (
                                                    <label key={type} className="flex items-center text-sm">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedProcedureTypes.includes(type)}
                                                            onChange={(e) => {
                                                                if (e.target.checked) {
                                                                    setSelectedProcedureTypes([...selectedProcedureTypes, type]);
                                                                } else {
                                                                    setSelectedProcedureTypes(selectedProcedureTypes.filter(t => t !== type));
                                                                }
                                                            }}
                                                            className="mr-2"
                                                        />
                                                        <span>{type}</span>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Search buttons */}
                            <div className="flex gap-4 mb-8">
                                <button
                                    onClick={handleSearch}
                                    disabled={isSearching}
                                    className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-lg font-semibold"
                                >
                                    {isSearching ? 'Meklē...' : 'Meklēt iepirkumus'}
                                </button>
                            </div>
                            
                            {/* Results */}
                            {searchResults && (
                                <div className="bg-white rounded-lg shadow p-6">
                                    <div className="flex justify-between items-center mb-4">
                                        <h2 className="text-xl font-semibold">
                                            {searchResults.totalFound > 0 
                                                ? `Atrasti ${searchResults.totalFound} rezultāti`
                                                : 'Nav atrasti rezultāti'}
                                        </h2>
                                        {searchResults.totalFound > 0 && (
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => downloadResults('json')}
                                                    className="text-sm bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700"
                                                >
                                                    Lejupielādēt JSON
                                                </button>
                                                <button
                                                    onClick={() => downloadResults('csv')}
                                                    className="text-sm bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700"
                                                >
                                                    Lejupielādēt CSV
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                    
                                    {searchResults.totalFound > 0 && (
                                        <div className="space-y-4">
                                            {searchResults.results.map((result) => {
                                                const expired = isDeadlineExpired(result.deadline);
                                                return (
                                                    <div key={result.id} className={`border ${expired ? 'border-red-200 bg-red-50' : 'border-gray-200'} rounded-lg p-4 hover:shadow-md`}>
                                                        <div className="flex justify-between items-start mb-2">
                                                            <h3 className="text-lg font-semibold text-blue-600 flex-1">{result.title}</h3>
                                                            <div className="flex items-center gap-2">
                                                                {expired && (
                                                                    <span className="text-xs px-2 py-1 rounded bg-red-100 text-red-800">
                                                                        Beidzies
                                                                    </span>
                                                                )}
                                                                <span className={`text-xs px-2 py-1 rounded ${
                                                                    result.status === 'IZSLUDINĀTS' ? 'bg-blue-100 text-blue-800' :
                                                                    result.status === 'PIEDĀVĀJUMI ATVĒRTI' ? 'bg-yellow-100 text-yellow-800' :
                                                                    result.status === 'LĪGUMS NOSLĒGTS' ? 'bg-green-100 text-green-800' :
                                                                    'bg-red-100 text-red-800'
                                                                }`}>
                                                                    {result.status}
                                                                </span>
                                                                <span className="text-sm text-gray-500">{result.date}</span>
                                                            </div>
                                                        </div>
                                                        <p className="text-gray-700 mb-2">{result.authority}</p>
                                                        {result.procedureType && (
                                                            <p className="text-sm text-purple-600 mb-2">{result.procedureType}</p>
                                                        )}
                                                        {result.authorityAddress && (
                                                            <p className="text-sm text-gray-600 mb-2">{result.authorityAddress}</p>
                                                        )}
                                                        <div className="flex flex-wrap gap-4 text-sm">
                                                            <span>CPV: {result.cpvCodes.join(', ')}</span>
                                                            <span className="font-semibold text-green-600">{formatValue(result.value)}</span>
                                                            <span className={`${expired ? 'text-red-600 font-semibold' : 'text-red-600'}`}>
                                                                Termiņš: {result.deadline}
                                                            </span>
                                                        </div>
                                                        <div className="mt-2">
                                                            <span className="text-sm text-gray-600">Atrasti vārdi: </span>
                                                            {result.matchedKeywords.map((kw, i) => (
                                                                <span key={i} className="text-sm bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded ml-1">
                                                                    {kw}
                                                                </span>
                                                            ))}
                                                        </div>
                                                        
                                                        {/* Izvērst/Sakļaut poga */}
                                                        <button
                                                            onClick={() => setExpandedResults({
                                                                ...expandedResults,
                                                                [result.id]: !expandedResults[result.id]
                                                            })}
                                                            className="mt-3 text-blue-600 hover:text-blue-800 text-sm font-medium"
                                                        >
                                                            {expandedResults[result.id] ? 'Sakļaut' : 'Izvērst papildu informāciju'}
                                                        </button>
                                                        
                                                        {/* Izvērstā informācija */}
                                                        {expandedResults[result.id] && (
                                                            <div className="mt-3 pt-3 border-t border-gray-200 space-y-2 text-sm">
                                                                <div className="grid md:grid-cols-2 gap-2">
                                                                    <div>
                                                                        <span className="font-medium text-gray-600">Izsludināšanas datums:</span>
                                                                        <span className="ml-2">{result.publicationDate || 'Nav norādīts'}</span>
                                                                    </div>
                                                                    <div>
                                                                        <span className="font-medium text-gray-600">Identifikācijas numurs:</span>
                                                                        <span className="ml-2">{result.identificationNumber || 'Nav norādīts'}</span>
                                                                    </div>
                                                                    <div>
                                                                        <span className="font-medium text-gray-600">Iesniegšanas termiņš:</span>
                                                                        <span className="ml-2">{result.deadline || 'Nav norādīts'}</span>
                                                                    </div>
                                                                    {result.duration && (
                                                                        <div>
                                                                            <span className="font-medium text-gray-600">Ilgums:</span>
                                                                            <span className="ml-2">{result.duration}</span>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                                
                #!/usr/bin/env python3
"""
Flask API serveris iepirkumu meklētājam ar uzlabotiem rezultātiem
FAILS: app.py - Atjaunināta versija
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import sys
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Importē uzlaboto meklētāja moduli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from local_procurement_searcher import IepirkumuMekletajs, LokalaisMekletajs

app = Flask(__name__)
CORS(app)  # Atļauj cross-origin pieprasījumus

# Logging
logging.basicConfig(level=logging.INFO)

# Globāla meklētāja instance
mekletajs = None

@app.route('/')
def index():
    """Servē pilnu HTML lapu ar UI"""
    return '''
    <!DOCTYPE html>
    <html lang="lv">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Iepirkumu meklētājs</title>
        <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body>
        <div id="root"></div>
        
        <script type="text/babel">
            const { useState, useEffect } = React;
            
            // API base URL
            const API_BASE = '';
            
            function ProcurementSearchUI() {
                const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
                const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
                const [keywords, setKeywords] = useState([]);
                const [newKeyword, setNewKeyword] = useState('');
                const [cpvCodes, setCpvCodes] = useState([]);
                const [newCpvCode, setNewCpvCode] = useState('');
                const [excludeKeywords, setExcludeKeywords] = useState([]);
                const [newExcludeKeyword, setNewExcludeKeyword] = useState('');
                const [isSearching, setIsSearching] = useState(false);
                const [searchResults, setSearchResults] = useState(null);
                const [error, setError] = useState(null);
                const [defaultConfig, setDefaultConfig] = useState(null);
                const [systemStatus, setSystemStatus] = useState(null);
                const [selectedStatuses, setSelectedStatuses] = useState(['IZSLUDINĀTS']);
                const [expandedResults, setExpandedResults] = useState({});
                const [resultView, setResultView] = useState('grid'); // 'grid' vai 'table'
                
                // Jaunie filtri
                const [deadlineStatus, setDeadlineStatus] = useState('all'); // 'all', 'active', 'expired'
                const [selectedProcedureTypes, setSelectedProcedureTypes] = useState([
                    'Atklāts konkurss virs ES sliekšņiem',
                    'Atklāts konkurss zem ES sliekšņiem',
                    'Slēgts konkurss virs ES sliekšņiem',
                    'Slēgts konkurss zem ES sliekšņiem',
                    'Sarunu procedūra virs ES sliekšņiem',
                    'Sarunu procedūra zem ES sliekšņiem',
                    'SPSIL atklāts konkurss',
                    'SPSIL slēgts konkurss',
                    'Cenu aptauja',
                    'Mazie iepirkumi'
                ]);
                
                // Procedūras tipu grupas
                const procedureGroups = {
                    'PIL virs ES sliekšņiem': [
                        'Atklāts konkurss virs ES sliekšņiem',
                        'Slēgts konkurss virs ES sliekšņiem',
                        'Sarunu procedūra virs ES sliekšņiem',
                        'Konkursa dialogs virs ES sliekšņiem',
                        'Konkursa procedūra ar sarunām virs ES sliekšņiem',
                        'Inovāciju partnerības procedūra virs ES sliekšņiem'
                    ],
                    'PIL zem ES sliekšņiem': [
                        'Atklāts konkurss zem ES sliekšņiem',
                        'Slēgts konkurss zem ES sliekšņiem',
                        'Sarunu procedūra zem ES sliekšņiem'
                    ],
                    'SPSIL': [
                        'SPSIL atklāts konkurss',
                        'SPSIL slēgts konkurss',
                        'SPSIL sarunu procedūra'
                    ],
                    'Citi': [
                        'Cenu aptauja',
                        'Mazie iepirkumi',
                        'Metu konkurss',
                        'Vispārīgā vienošanās'
                    ]
                };
                
                // Ielādē noklusējuma konfigurāciju un statusu
                useEffect(() => {
                    fetch('/api/config')
