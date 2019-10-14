
var canvas = document.getElementById('canvas')
var ctx = canvas.getContext('2d')

canvas.addEventListener('mousedown', HandleMouseDown)

// Tiles for the game board
var tiles = []

var numRows = 100
var numCols = 100
var numTiles = numRows * numCols

var tileWidth = 10
var tileHeight = 10

// var transportMatrix = math.matrix(math.zeros([numTiles, numTiles])) // for transport of humidity and temp
var diffusionMatrix = math.zeros([numTiles, numTiles], 'sparse') // for diffusion of humidity and temp

console.log({ numTiles })

var humidityVector = math.zeros(numTiles) // to measure humidity
var temperatureVector = math.zeros(numTiles) // to measure temperature

console.log({ diffusionMatrix })
console.log({ temperatureVector })

function getTileByIndices (i, j) {
  return tiles.filter(tile => { return tile.row === i && tile.column === j })[0]
}

function getTileByIndex (index) {
  return tiles.filter(tile => { return tile.index === index })[0]
}

function haversineDistance (coords1, coords2, isMiles) {
  function toRad (x) {
    return x * Math.PI / 180
  }

  var lon1 = coords1[0]
  var lat1 = coords1[1]

  var lon2 = coords2[0]
  var lat2 = coords2[1]

  var R = 6371 // km

  var x1 = lat2 - lat1
  var dLat = toRad(x1)
  var x2 = lon2 - lon1
  var dLon = toRad(x2)
  var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2)
  var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  var d = R * c

  if (isMiles) d /= 1.60934

  return d
}

function ZeroAltitudeInit () {
  var indexer = 0
  for (let i = 0; i < numRows; i++) {
    for (let j = 0; j < numCols; j++) {
      tiles.push({
        index: indexer,
        row: i,
        column: j,
        lon: j * 360 / numRows,
        lat: 90 - i * 180 / numRows,
        temperature: 10,
        altitude: 0,
        albedo: 0.5,
        humidity: 0,
        pressure: 0
      })
      indexer = indexer + 1
    }
  }
} function OneAltitudeInit () {
  var indexer = 0
  for (let i = 0; i < numRows; i++) {
    for (let j = 0; j < numCols; j++) {
      tiles.push({
        index: indexer,
        row: i,
        column: j,
        lon: j * 360 / numRows,
        lat: 90 - i * 180 / numRows,
        temperature: 10,
        altitude: 1,
        albedo: 0.5,
        humidity: 0,
        pressure: 0
      })
      indexer = indexer + 1
    }
  }
}

function RandomAltitudeInit () {
  var indexer = 0
  for (let i = 0; i < numRows; i++) {
    for (let j = 0; j < numCols; j++) {
      tiles.push({
        index: indexer,
        row: i,
        column: j,
        lon: j * 360 / numRows,
        lat: 90 - i * 180 / numRows,
        temperature: 30,
        altitude: Math.floor(-2 + Math.random() * 5),
        albedo: 0.5,
        humidity: 0,
        pressure: 0
      })
      indexer = indexer + 1
    }
  }
}

var globalSeaLevel = 0

function HandleMouseDown (mouseEvent) {
  // Identify tile
  tileSelected = getTileByIndices(
    Math.floor(mouseEvent.offsetY / tileWidth),
    Math.floor(mouseEvent.offsetX / tileHeight)
  )
  tileSelected.altitude = 3
  // DrawTile('land', tileSelected)
}

function DrawTile (attribute, tile) {
  if (attribute === 'land') {
    if (tile.altitude > globalSeaLevel) {
      if (tile.temperature < 0) { ctx.fillStyle = 'rgb(249, 242, 236)' } else { ctx.fillStyle = 'rgb(204, 153, 0)' }
    } else {
      if (tile.temperature < 0) { ctx.fillStyle = 'rgb(250, 250, 250' } else { ctx.fillStyle = 'rgb(51, 204, 255)' }
    }
  }
  if (attribute === 'temperature') {
    var adjustedTemp = Math.min(255, Math.max(0, tile.temperature * (255 - 60) / 60))
    ctx.fillStyle = `rgb(${adjustedTemp}, ${255 - adjustedTemp}, ${255 - adjustedTemp})`
  }
  ctx.fillRect(tile.column * tileHeight, tile.row * tileWidth, tileWidth, tileHeight)
}

function SetTempByLatitude () {
  tiles.map(tile => { tile.temperature = -10 + Math.cos(tile.lat * 2 * Math.PI / 360) * 60 })
}

function DrawMap (attribute) {
  tiles.map(tile => DrawTile(attribute, tile))
}

var altitudeVector = math.matrix(tiles.map(tile => tile.altitude))
var albedoVector = math.matrix(tiles.map(tile => tile.albedo))

/**
 * to be done once, at the start
 *
 * using math.js as linear alg library
 * defines the transport matrix (applied to humidity and temperature for transport component of update)
 * defines the diffusion matrix (applied to humidity and temperature for diffusion component of update)
 */
function AssembleMatrices () {
  tiles.map(tile => {
    const j = tile.index
    const row = tile.row
    const col = tile.column
    // from tile j to ...
    // edge cases:
    // row === 0
    if (row === 0) {
      // east
      const eastCol = ((col - 1) + numCols) % numCols
      const eastTile = getTileByIndices(row, eastCol)
      const eastI = eastTile.index
      const distToEastTile = haversineDistance([tile.lon, tile.lat], [eastTile.lon, eastTile.lat], false)
      // west
      const westCol = ((col + 1) + numCols) % numCols
      const westTile = getTileByIndices(row, westCol)
      const westI = eastTile.index
      const distToWestTile = haversineDistance([tile.lon, tile.lat], [westTile.lon, westTile.lat], false)
      // south
      const southTile = getTileByIndices(row + 1, col)
      const southI = southTile.index
      const distToSouthTile = haversineDistance([tile.lon, tile.lat], [southTile.lon, southTile.lat], false)

      const totalDist = distToEastTile + distToWestTile + distToSouthTile

      diffusionMatrix.subset(math.index(eastI, j), diffusionMatrix.subset(math.index(eastI, j)) + distToEastTile / totalDist)
      diffusionMatrix.subset(math.index(westI, j), diffusionMatrix.subset(math.index(westI, j)) + distToWestTile / totalDist)
      diffusionMatrix.subset(math.index(southI, j), diffusionMatrix.subset(math.index(southI, j)) + distToSouthTile / totalDist)
    } else if (row === numRows - 1) {
      // east
      const eastCol = ((col - 1) + numCols) % numCols
      const eastTile = getTileByIndices(row, eastCol)
      const eastI = eastTile.index
      const distToEastTile = haversineDistance([tile.lon, tile.lat], [eastTile.lon, eastTile.lat], false)
      // west
      const westCol = ((col + 1) + numCols) % numCols
      const westTile = getTileByIndices(row, westCol)
      const westI = eastTile.index
      const distToWestTile = haversineDistance([tile.lon, tile.lat], [westTile.lon, westTile.lat], false)
      // north
      const northTile = getTileByIndices(row - 1, col)
      const northI = northTile.index
      const distToNorthTile = haversineDistance([tile.lon, tile.lat], [northTile.lon, northTile.lat], false)

      const totalDist = distToEastTile + distToWestTile + distToNorthTile

      diffusionMatrix.subset(math.index(eastI, j), diffusionMatrix.subset(math.index(eastI, j)) + distToEastTile / totalDist)
      diffusionMatrix.subset(math.index(westI, j), diffusionMatrix.subset(math.index(westI, j)) + distToWestTile / totalDist)
      diffusionMatrix.subset(math.index(northI, j), diffusionMatrix.subset(math.index(northI, j)) + distToNorthTile / totalDist)
    } else {
      // east
      const eastCol = ((col - 1) + numCols) % numCols
      const eastTile = getTileByIndices(row, eastCol)
      const eastI = eastTile.index
      const distToEastTile = haversineDistance([tile.lon, tile.lat], [eastTile.lon, eastTile.lat], false)
      // west
      const westCol = ((col + 1) + numCols) % numCols
      const westTile = getTileByIndices(row, westCol)
      const westI = eastTile.index
      const distToWestTile = haversineDistance([tile.lon, tile.lat], [westTile.lon, westTile.lat], false)
      // north
      const northTile = getTileByIndices(row - 1, col)
      const northI = northTile.index
      const distToNorthTile = haversineDistance([tile.lon, tile.lat], [northTile.lon, northTile.lat], false)
      // south
      const southTile = getTileByIndices(row + 1, col)
      const southI = southTile.index
      const distToSouthTile = haversineDistance([tile.lon, tile.lat], [southTile.lon, southTile.lat], false)

      const totalDist = distToEastTile + distToWestTile + distToNorthTile + distToSouthTile

      diffusionMatrix.subset(math.index(eastI, j), diffusionMatrix.subset(math.index(eastI, j)) + distToEastTile / totalDist)
      diffusionMatrix.subset(math.index(westI, j), diffusionMatrix.subset(math.index(westI, j)) + distToWestTile / totalDist)
      diffusionMatrix.subset(math.index(northI, j), diffusionMatrix.subset(math.index(northI, j)) + distToNorthTile / totalDist)
      diffusionMatrix.subset(math.index(southI, j), diffusionMatrix.subset(math.index(southI, j)) + distToSouthTile / totalDist)
    }
  })
}

var insolation = 200
var stefanBoltzmannConst = 0.000000005

var evaporationCoefficient = 0.6 // temperature --> humidity

var diffusionCoefficient = 0.1 // how much heat and humidity go from one tile to neighbors

var transportationCoefficient = 0.9 // how much heat and humidity go from one tile to neighbors

function UpdateClimate (delta) {
  var increment = delta / 1000
  // humidityVector = increment * diffusionCoefficient * math.multiply(diffusionMatrix, humidityVector)
  temperatureVector = math.add(math.multiply(math.multiply(diffusionMatrix, temperatureVector), diffusionCoefficient),
    math.multiply(temperatureVector, (1 - diffusionCoefficient)))
  // TODO: + increment * albedoVector * insolationVector
  //  tile.temperature = tile.temperature + increment * tile.albedo * Math.cos(tile.lat * 2 * Math.PI / 360) * insolation
  tiles.map(tile => {
    tile.humidity = math.subset(humidityVector, math.index(tile.index))
    tile.temperature = math.subset(temperatureVector, math.index(tile.index))
  })
}

/**
 * Tile update
 * Mechanisms:
 *  air temperature updates from
 *      insolation
 *      transport
 *      diffusion
 *  air humidity updates from
 *      rainfall
 *      evaporation
 *  pressure depends entirely on altitude
 *  TO ADD:
 *      water currents
 *
 */
function UpdateTile (delta, tile) {
  // update tile albedo based on temperature (< 0 ---> snow on ground ---> zero albedo)
  if (tile.temperature < 0) { tile.albedo = 0.1 } // snow/ice
  else if (tile.altitude > 0) { tile.albedo = 0.3 } // water
  else { tile.albedo = 0.7 } // land
  // console.log(tile)
}

function OnTick (delta) {
  UpdateClimate(delta)
  tiles.map(tile => UpdateTile(delta, tile))
}

function getAvg (attribute) {
  const total = tiles.map(tile => tile[attribute]).reduce((acc, c) => acc + c, 0)
  return total / tiles.length
}
function getMax (attribute) {
  const total = tiles.map(tile => tile[attribute]).reduce((acc, c) => math.max(acc, c), 0)
  return total
}

var attributeToDraw = 'temperature'

var temperatureButton = document.getElementById('temperatureButton')
temperatureButton.addEventListener('click', () => { attributeToDraw = 'temperature' })
var landSeaButton = document.getElementById('landSeaButton')
landSeaButton.addEventListener('click', () => { attributeToDraw = 'land' })

var PAUSE = false
var pauseButton = document.getElementById('PAUSE')
pauseButton.addEventListener('click', () => { PAUSE = !PAUSE })

OneAltitudeInit()

temperatureVector.subset(math.index(277), 10000)

var limit = 10
var lastFrameTimeMs = 0
var maxFPS = 5
var delta = 0
var timestep = 1000 / 60

function panic () {
  delta = 0
}

var numUpdates = 0
function mainLoop (timestamp) {
  // Throttle the frame rate.
  if (timestamp < lastFrameTimeMs + (1000 / maxFPS)) {
    requestAnimationFrame(mainLoop)
    return
  }
  delta += timestamp - lastFrameTimeMs
  lastFrameTimeMs = timestamp

  var numUpdateSteps = 0
  while (delta >= timestep) {
    OnTick(timestep)
    numUpdates += 1
    console.log(`Average temp: ${getAvg('temperature')}`)
    console.log(`Max temperature: ${getMax('temperature')}`)
    delta -= timestep
    if (++numUpdateSteps >= 240) {
      panic()
      break
    }
    if (numUpdates > limit) { panic(); process.exit(1) }
  }
  DrawMap(attributeToDraw)
  requestAnimationFrame(mainLoop)
}

requestAnimationFrame(mainLoop)
